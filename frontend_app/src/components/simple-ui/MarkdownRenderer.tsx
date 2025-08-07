
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: (props) => <a {...props} className="text-blue-600 underline" />,
        code: (props) => <code {...props} className="bg-gray-100 px-1 rounded text-xs" />,
        pre: (props) => <pre {...props} className="bg-gray-100 p-2 rounded text-xs overflow-x-auto" />,
        h1: (props) => <h1 {...props} className="text-xl font-bold mt-4 mb-2" />,
        h2: (props) => <h2 {...props} className="text-lg font-bold mt-3 mb-2" />,
        h3: (props) => <h3 {...props} className="text-base font-bold mt-2 mb-1" />,
        ul: (props) => <ul {...props} className="list-disc ml-6" />,
        ol: (props) => <ol {...props} className="list-decimal ml-6" />,
        li: (props) => <li {...props} className="mb-1" />,
        blockquote: (props) => <blockquote {...props} className="border-l-4 border-blue-200 pl-3 italic text-gray-600" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
