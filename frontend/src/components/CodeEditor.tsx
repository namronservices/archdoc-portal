import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";

interface Props {
  defaultValue: string;
  onChange: (value: string) => void;
}

/** Minimal CodeMirror 6 editor used for Mermaid diagram source. */
export default function CodeEditor({ defaultValue, onChange }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!hostRef.current) return;
    const view = new EditorView({
      doc: defaultValue,
      extensions: [
        basicSetup,
        EditorView.lineWrapping,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChangeRef.current(update.state.doc.toString());
          }
        }),
      ],
      parent: hostRef.current,
    });
    return () => view.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      ref={hostRef}
      className="overflow-hidden rounded border border-slate-300 text-sm"
    />
  );
}
