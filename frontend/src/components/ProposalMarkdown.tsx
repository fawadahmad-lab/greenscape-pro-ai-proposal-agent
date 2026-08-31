import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ProposalMarkdownProps {
  content: string | null;
}

export default function ProposalMarkdown({ content }: ProposalMarkdownProps) {
  if (!content) return null;
  return (
    <div className="proposal-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
