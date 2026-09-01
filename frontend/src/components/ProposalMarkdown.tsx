import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface ProposalMarkdownProps {
  content: string | null;
}

const components: Components = {
  table: (props) => (
    <div className="table-scroll">
      <table {...props} />
    </div>
  ),
};

export default function ProposalMarkdown({ content }: ProposalMarkdownProps) {
  if (!content) return null;
  return (
    <div className="proposal-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
