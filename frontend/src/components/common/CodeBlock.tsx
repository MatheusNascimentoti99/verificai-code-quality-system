import React from 'react';

interface CodeBlockProps {
  code: string;
  language: string;
  fileName?: string;
  lineNumbers?: [number, number];
}

const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language,
  fileName,
  lineNumbers
}) => {
  const getLanguageClass = (lang: string) => {
    switch (lang.toLowerCase()) {
      case 'python':
        return 'language-python';
      case 'javascript':
      case 'js':
        return 'language-javascript';
      case 'typescript':
      case 'ts':
        return 'language-typescript';
      case 'java':
        return 'language-java';
      case 'cpp':
      case 'c++':
        return 'language-cpp';
      case 'c':
        return 'language-c';
      case 'html':
        return 'language-html';
      case 'css':
        return 'language-css';
      case 'sql':
        return 'language-sql';
      case 'json':
        return 'language-json';
      case 'xml':
        return 'language-xml';
      case 'yaml':
      case 'yml':
        return 'language-yaml';
      default:
        return 'language-plaintext';
    }
  };

  const formatCodeWithLines = (code: string, startLine?: number, endLine?: number) => {
    if (!startLine || !endLine) {
      return { formattedLines: code.split('\n'), lineNumbers: null };
    }

    const lines = code.split('\n');
    const lineNumbers = [];
    const formattedLines = [];

    for (let i = 0; i < lines.length; i++) {
      const lineNumber = startLine + i;
      lineNumbers.push(lineNumber);
      formattedLines.push(lines[i]);
    }

    return {
      formattedLines,
      lineNumbers
    };
  };

  const codeContent = lineNumbers
    ? formatCodeWithLines(code, lineNumbers[0], lineNumbers[1])
    : { formattedLines: code.split('\n'), lineNumbers: null };

  return (
    <div className="relative">
      {/* Header */}
      {(fileName || language) && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 text-gray-200 text-sm rounded-t-lg">
          <div className="flex items-center gap-2">
            {fileName && (
              <span className="font-medium">{fileName}</span>
            )}
            <span className="text-gray-400">
              {language.toUpperCase()}
            </span>
          </div>
          {lineNumbers && (
            <span className="text-xs text-gray-400">
              Linhas {lineNumbers[0]}-{lineNumbers[1]}
            </span>
          )}
        </div>
      )}

      {/* Code Content */}
      <div className={`bg-gray-900 rounded-lg ${!fileName && !language ? 'rounded-t-lg' : 'rounded-t-none'}`}>
        <pre className="overflow-x-auto p-4 text-sm">
          <code className={getLanguageClass(language)}>
            {codeContent.formattedLines.map((line, index) => (
              <div key={index} className="flex">
                {/* Line numbers */}
                {codeContent.lineNumbers && (
                  <span className="text-gray-500 text-right pr-4 select-none min-w-[50px]">
                    {codeContent.lineNumbers[index]}
                  </span>
                )}
                {/* Code line */}
                <span className="text-gray-300">{line || ' '}</span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
};

export default CodeBlock;