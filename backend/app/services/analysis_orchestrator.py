"""
Analysis orchestrator for VerificAI Backend
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

from app.models.analysis import Analysis, AnalysisStatus
from app.models.prompt import Prompt
from app.core.config import settings
from app.services.llm_provider import LLMProvider
from app.services.file_processor import FileProcessor
from app.services.token_optimizer import TokenOptimizer
from app.services.analysis_queue import AnalysisQueue

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Analysis type enumeration"""
    GENERAL = "general"
    ARCHITECTURE = "architecture"
    RULES = "rules"


class AnalysisConfig:
    """Configuration for analysis jobs"""

    def __init__(
        self,
        analysis_type: AnalysisType,
        files: List[str],
        prompt_content: str,
        llm_provider: str = 'openai',
        max_tokens: int = 32000,  # Aumentado drasticamente para acomodar análises completas
        temperature: float = 0.7,
        **kwargs
    ):
        self.analysis_type = analysis_type
        self.files = files
        self.prompt_content = prompt_content
        self.llm_provider = llm_provider
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.kwargs = kwargs


class AnalysisOrchestrator:
    """Main orchestrator for analysis operations"""

    def __init__(self):
        self.queue = AnalysisQueue()
        self.llm_provider = LLMProvider()
        self.file_processor = FileProcessor()
        self.token_optimizer = TokenOptimizer()
        self.active_jobs: Dict[str, Analysis] = {}

    async def start_analysis(self, analysis: Analysis) -> str:
        """Start a new analysis job"""
        logger.info(f"Starting analysis {analysis.id} for user {analysis.user_id}")

        # Check if there's already an active analysis
        active_job = await self.queue.get_active_job()
        if active_job:
            raise ValueError("An analysis is already running. Please wait for it to complete.")

        # Parse configuration
        config = self._parse_analysis_config(analysis)

        # Add to queue
        await self.queue.enqueue(analysis)

        # Start processing in background
        asyncio.create_task(self._process_analysis_async(analysis.id, config))

        return analysis.id

    async def cancel_analysis(self, analysis_id: str) -> bool:
        """Cancel a running analysis"""
        logger.info(f"Cancelling analysis {analysis_id}")

        # Get from active jobs
        if analysis_id in self.active_jobs:
            analysis = self.active_jobs[analysis_id]
            analysis.cancel_processing()

            # Remove from active jobs
            del self.active_jobs[analysis_id]

            # Mark as cancelled in queue
            await self.queue.fail_job(analysis_id, "Cancelled by user")

            return True

        return False

    async def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """Get current analysis status"""
        # Get from queue
        job = await self.queue.get_job(analysis_id)
        if not job:
            return {"status": "not_found"}

        return {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress_percentage,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message
        }

    async def _process_analysis_async(self, analysis_id: int, config: AnalysisConfig) -> None:
        """Process analysis job asynchronously"""
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            # Get analysis from database
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if not analysis:
                logger.error(f"Analysis {analysis_id} not found")
                return

            # Add to active jobs
            self.active_jobs[str(analysis_id)] = analysis

            # Update status to processing
            analysis.start_processing()
            db.commit()

            # Process analysis
            result = await self._process_analysis(analysis, config)

            # Complete analysis
            analysis.complete_processing()

            # Create result
            from app.models.analysis import AnalysisResult
            analysis_result = AnalysisResult(
                analysis_id=analysis.id,
                summary=result.get('overall_assessment', ''),
                detailed_findings=result.get('detailed_findings', ''),
                recommendations=result.get('recommendations', ''),
                confidence=result.get('confidence', 0.0),
                model_used=result.get('model_used', ''),
                tokens_used=result.get('token_usage', {}).get('total_tokens', 0),
                processing_time=result.get('processing_time', 0),
                issues=result.get('criteria_results', []),
                metrics=result.get('metrics', {}),
                code_snippets=result.get('code_examples', []),
                file_analysis=result.get('file_analysis', {})
            )

            db.add(analysis_result)
            db.commit()

            # Calculate scores
            analysis.calculate_scores()
            db.commit()

            # Mark as complete in queue
            await self.queue.complete_job(str(analysis_id), result)

            logger.info(f"Analysis {analysis_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing analysis {analysis_id}: {str(e)}")

            # Mark as failed
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.fail_processing(str(e))
                db.commit()

                # Mark as failed in queue
                await self.queue.fail_job(str(analysis_id), str(e))

        finally:
            # Remove from active jobs
            if str(analysis_id) in self.active_jobs:
                del self.active_jobs[str(analysis_id)]

            db.close()

    async def _process_analysis(self, analysis: Analysis, config: AnalysisConfig) -> Dict[str, Any]:
        """Process a single analysis job"""
        logger.info(f"Processing analysis {analysis.id}")

        start_time = datetime.utcnow()

        try:
            # Step 1: Update progress - 10%
            await self.queue.update_progress(str(analysis.id), 10)

            # Step 2: Process files - 30%
            raw_processed_files = await self.file_processor.process_files(config.files)
            processed_files = [f.to_dict() for f in raw_processed_files]
            logger.info(f"Successfully processed {len(processed_files)} files for analysis {analysis.id}")
            await self.queue.update_progress(str(analysis.id), 30)

            # Step 3: Optimize content - 50%
            optimized_content = self.token_optimizer.optimize_content(processed_files, config.max_tokens)
            await self.queue.update_progress(str(analysis.id), 50)

            # Step 4: Execute LLM analysis - 80%
            llm_response = await self.llm_provider.analyze_with_fallback(
                config.prompt_content,
                optimized_content,
                config.llm_provider,
                config.temperature,
                config.max_tokens  # Adicionando max_tokens que estava faltando!
            )
            await self.queue.update_progress(str(analysis.id), 80)

            # Step 5: Process results - 100%
            result = self._process_llm_response(llm_response, processed_files, config)

            # Add metadata
            result['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
            result['model_used'] = llm_response.get('model', 'unknown')
            result['token_usage'] = llm_response.get('usage', {})

            await self.queue.update_progress(str(analysis.id), 100)

            return result

        except Exception as e:
            logger.error(f"Error in analysis processing: {str(e)}")
            raise

    def _parse_analysis_config(self, analysis: Analysis) -> AnalysisConfig:
        """Parse analysis configuration from database model"""
        # Extract files from analysis
        files = analysis.get_file_paths()

        # Get prompt content
        prompt_content = analysis.prompt.content if analysis.prompt else ""

        # Get configuration
        config_data = analysis.get_configuration()

        return AnalysisConfig(
            analysis_type=AnalysisType.GENERAL,  # Default to general
            files=files,
            prompt_content=prompt_content,
            llm_provider=config_data.get('llm_provider', 'openai'),
            max_tokens=config_data.get('max_tokens', 32000),  # Aumentado para evitar truncamento
            temperature=config_data.get('temperature', 0.7)
        )

    def _process_llm_response(self, llm_response: Dict[str, Any], processed_files: List[Dict[str, Any]], config: AnalysisConfig) -> Dict[str, Any]:
        """Process LLM response and format results"""
        content = llm_response.get('content', '')
        
        # Initialize default result
        result = {
            'overall_assessment': content,
            'criteria_results': [],
            'code_examples': [],
            'recommendations': [],
            'confidence': 0.8,
            'detailed_findings': content,
            'metrics': {
                'total_files': len(processed_files),
                'total_lines': sum(f.get('line_count', 0) for f in processed_files),
                'languages_analyzed': list(set(f.get('language', '') for f in processed_files))
            },
            'file_analysis': {}
        }
        
        # Try to extract JSON from response
        try:
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                
            if json_match:
                json_str = json_match.group(1) if len(json_match.groups()) > 0 else json_match.group(0)
                json_data = json.loads(json_str)
                
                # Merge parsed data into result
                if isinstance(json_data, dict):
                    result['overall_assessment'] = json_data.get('overall_assessment', content)
                    result['detailed_findings'] = json_data.get('detailed_findings', content)
                    result['criteria_results'] = json_data.get('criteria_results', [])
                    result['code_examples'] = json_data.get('code_examples', [])
                    result['recommendations'] = json_data.get('recommendations', [])
                    result['confidence'] = json_data.get('confidence', 0.8)
                    
                    # Merge metrics if provided
                    if 'metrics' in json_data:
                        result['metrics'].update(json_data['metrics'])
        except Exception as e:
            logger.warning(f"Failed to parse LLM response as JSON: {str(e)}")

        # Add file-specific metadata if not already present
        for file_info in processed_files:
            if file_info['path'] not in result['file_analysis']:
                result['file_analysis'][file_info['path']] = {
                    'language': file_info.get('language', ''),
                    'line_count': file_info.get('line_count', 0),
                    'size_bytes': file_info.get('size', 0)
                }

        return result

    async def get_active_analysis(self) -> Optional[Dict[str, Any]]:
        """Get currently active analysis"""
        job = await self.queue.get_active_job()
        if not job:
            return None

        return {
            'job_id': job.id,
            'name': job.name,
            'status': job.status,
            'progress': job.progress_percentage,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'user_id': job.user_id
        }