import { useEffect, useRef } from "react";
import { Crepe } from "@milkdown/crepe";

interface Props {
  /** Initial Markdown. The editor is uncontrolled after mount. */
  defaultValue: string;
  onChange: (markdown: string) => void;
}

/**
 * Milkdown (Crepe) WYSIWYG Markdown editor.
 *
 * Mount one per section — give the parent a `key` of the section id so the
 * editor re-initialises with fresh content when the selection changes.
 */
export default function MilkdownEditor({ defaultValue, onChange }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!hostRef.current) return;
    const crepe = new Crepe({
      root: hostRef.current,
      defaultValue,
    });
    crepe.on((listener) => {
      listener.markdownUpdated((_ctx, markdown) => {
        onChangeRef.current(markdown);
      });
    });
    crepe.create().catch((e) => console.error("Milkdown init failed", e));

    return () => {
      crepe.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={hostRef} className="milkdown-host" />;
}
