const techStack = [
  "Pydantic AI",
  "FastAPI",
  "React",
  "OpenAI GPT",
  "Railway",
];

function ArchNode({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <p className="font-medium text-gray-900 text-sm">{title}</p>
      <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      {children && <div className="mt-2 pl-3 border-l border-gray-200 space-y-1">{children}</div>}
    </div>
  );
}

function Connector() {
  return (
    <div className="flex justify-center">
      <div className="w-px h-5 bg-gray-300" />
    </div>
  );
}

export default function AboutPage() {
  return (
    <div className="space-y-10">
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">What is this?</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Invoice Auditor is an AI-powered auditing layer for Danish SMEs. It catches errors in
          vendor invoices - wrong amounts, VAT misclassification, currency conversions, and
          duplicates - before they reach your accounting software. Built as a personal project demo
          using Pydantic AI for structured LLM extraction, FastAPI for the REST API, and React for
          the frontend.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">How it works</h2>
        <ol className="space-y-3">
          {[
            {
              step: "1",
              title: "Image preprocessing",
              body: "Uploaded invoices are converted to a standardised JPEG regardless of input format (PNG, WEBP, PDF).",
            },
            {
              step: "2",
              title: "Pydantic AI agent",
              body: "A GPT agent extracts structured data from the image, calling two tools: lookup_vat checks each line item against Danish VAT rules, and validate_cvr validates the vendor CVR number against the Danish business registry.",
            },
            {
              step: "3",
              title: "Deterministic post-processing",
              body: "VAT math verification, currency conversion, and status assignment run as plain Python - not LLM - for reliability and testability.",
            },
            {
              step: "4",
              title: "Result",
              body: "The invoice is classified as Green (auto-approved), Review (needs human check), or Red (issues found), with flags describing each problem.",
            },
          ].map(({ step, title, body }) => (
            <li key={step} className="flex gap-3">
              <span className="flex-none w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold flex items-center justify-center mt-0.5">
                {step}
              </span>
              <div>
                <p className="text-sm font-medium text-gray-900">{title}</p>
                <p className="text-sm text-gray-600 leading-relaxed">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Architecture</h2>
        <div className="max-w-sm">
          <ArchNode title="Browser - React frontend" description="Drag-and-drop upload, real-time progress, result display" />
          <Connector />
          <ArchNode title="FastAPI (REST)" description="Receives image, returns structured Invoice JSON">
            <p className="text-xs text-gray-500">Image preprocessing - normalise to standardised JPEG</p>
          </ArchNode>
          <Connector />
          <ArchNode title="Pydantic AI agent" description="LLM extraction with tool calling">
            <p className="text-xs text-gray-500">
              <span className="font-mono text-gray-700">lookup_vat</span> - checks line items against Danish VAT rules
            </p>
            <p className="text-xs text-gray-500">
              <span className="font-mono text-gray-700">validate_cvr</span> - validates vendor CVR via the Danish registry
            </p>
          </ArchNode>
          <Connector />
          <ArchNode title="Deterministic post-audit" description="VAT math verification, currency conversion, and Green / Review / Red status assignment" />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Design philosophy</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          The key design split: the LLM agent handles the inherently fuzzy work - reading
          handwriting, parsing unstructured layouts, inferring missing fields. Everything that can
          be expressed as a rule - VAT arithmetic, CVR lookup, status thresholds - runs as plain
          Python in the post-audit layer, keeping it testable and reliable.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Tech stack</h2>
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech) => (
            <span
              key={tech}
              className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-700"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
