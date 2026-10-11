import { useRef, useCallback } from "react";
import "./SegmentedSwitch.css";

/**
 * Two-option segmented tab switch.
 *
 * @param {Object} props
 * @param {{ value: string, label: string }[]} props.options - Exactly two options
 * @param {string} props.value - Currently selected option value
 * @param {(value: string) => void} props.onChange - Called when a tab is selected
 * @param {string} [props.id] - Base ID for the tablist
 */
export default function SegmentedSwitch({ options, value, onChange, id = "mode-switch" }) {
  const tabRefs = useRef([]);

  const handleKeyDown = useCallback(
    (e) => {
      const currentIdx = options.findIndex((o) => o.value === value);
      let nextIdx;

      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        nextIdx = (currentIdx + 1) % options.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        nextIdx = (currentIdx - 1 + options.length) % options.length;
      } else if (e.key === "Home") {
        e.preventDefault();
        nextIdx = 0;
      } else if (e.key === "End") {
        e.preventDefault();
        nextIdx = options.length - 1;
      } else {
        return;
      }

      onChange(options[nextIdx].value);
      tabRefs.current[nextIdx]?.focus();
    },
    [options, value, onChange],
  );

  return (
    <div
      className="segmented-switch"
      role="tablist"
      aria-label="Input mode"
      id={id}
    >
      {options.map((opt, idx) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            ref={(el) => { tabRefs.current[idx] = el; }}
            role="tab"
            type="button"
            id={`${id}-tab-${opt.value}`}
            aria-selected={isSelected}
            aria-controls={`${id}-panel-${opt.value}`}
            tabIndex={isSelected ? 0 : -1}
            className={`segmented-switch-tab text-caption-lg${isSelected ? " segmented-switch-tab-active" : ""}`}
            onClick={() => onChange(opt.value)}
            onKeyDown={handleKeyDown}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
