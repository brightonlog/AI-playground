import { useState } from "react";

type Props = {
  value: string;
  maxLength: number;
  placeholder?: string;
  /** Called on Enter or blur when the text changed. */
  onSave: (text: string) => void;
  onCancel?: () => void;
  autoFocus?: boolean;
  className?: string;
};

/** Text input that saves on Enter or blur, and reverts on Escape. */
export default function TextField({ value, maxLength, placeholder, onSave, onCancel, autoFocus, className }: Props) {
  const [text, setText] = useState(value);
  const [prev, setPrev] = useState(value);
  if (value !== prev) {
    // A reload from the server replaces what is shown.
    setPrev(value);
    setText(value);
  }
  const save = () => {
    if (text.trim() !== value) onSave(text.trim());
    else onCancel?.();
  };
  return (
    <input
      value={text}
      maxLength={maxLength}
      placeholder={placeholder}
      autoFocus={autoFocus}
      onChange={(e) => setText(e.target.value)}
      onBlur={save}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
        if (e.key === "Escape") {
          setText(value);
          onCancel?.();
        }
      }}
      className={`rounded border border-zinc-300 px-2 py-1 text-sm ${className ?? ""}`}
    />
  );
}
