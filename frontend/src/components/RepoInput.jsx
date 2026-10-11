import { useState, useCallback, useId } from "react";
import { parseGithubUrl } from "../utils/githubUrl";
import "./RepoInput.css";

/**
 * GitHub repository URL input with inline validation.
 *
 * Validates on blur and on submit.
 * Clears the error as soon as the user edits the field.
 * Shows a "Will scan: github.com/owner/repo" confirmation when valid.
 *
 * @param {Object} props
 * @param {string} props.value - Current raw input value
 * @param {(value: string) => void} props.onChange - Called on every keystroke
 * @param {{ ok: true, owner: string, repo: string, url: string } | null} props.parsed
 *   Parsed result, kept in parent so it can gate the submit button.
 * @param {(parsed: ReturnType<typeof parseGithubUrl> | null) => void} props.onParsedChange
 * @param {() => void} [props.onSubmit] - Called when Enter is pressed and input is valid
 * @param {boolean} [props.disabled]
 */
export default function RepoInput({
  value,
  onChange,
  parsed,
  onParsedChange,
  onSubmit,
  disabled = false,
}) {
  const uid = useId();
  const inputId = `repo-input${uid}`;
  const errorId = `repo-error${uid}`;
  const helperId = `repo-helper${uid}`;
  const confirmId = `repo-confirm${uid}`;

  const [errorMessage, setErrorMessage] = useState(null);

  const handleChange = useCallback(
    (e) => {
      const v = e.target.value;
      onChange(v);
      // Clear error as soon as the user edits the field
      setErrorMessage(null);

      // Re-parse live so valid input immediately enables submit button and shows confirmation
      const result = parseGithubUrl(v);
      if (result.ok) {
        onParsedChange(result);
      } else {
        onParsedChange(null);
      }
    },
    [onChange, onParsedChange],
  );

  const handleBlur = useCallback(() => {
    const result = parseGithubUrl(value);
    if (!result.ok) {
      setErrorMessage(result.error);
      onParsedChange(null);
    } else {
      setErrorMessage(null);
      onParsedChange(result);
    }
  }, [value, onParsedChange]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const result = parseGithubUrl(value);
        if (!result.ok) {
          setErrorMessage(result.error);
          onParsedChange(null);
        } else {
          setErrorMessage(null);
          onParsedChange(result);
          if (onSubmit) {
            onSubmit();
          }
        }
      }
    },
    [value, onParsedChange, onSubmit],
  );

  const showError = Boolean(errorMessage);
  const showConfirm = Boolean(!errorMessage && parsed?.ok);

  const describedBy = showError
    ? errorId
    : showConfirm
      ? confirmId
      : helperId;

  return (
    <div className="repo-input-group form-group">
      <label htmlFor={inputId} className="text-caption-lg form-label repo-input-label">
        GITHUB REPOSITORY URL
      </label>

      <input
        id={inputId}
        type="text"
        inputMode="url"
        autoComplete="off"
        spellCheck={false}
        placeholder="https://github.com/owner/repo"
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className={`form-input${showError ? " form-input-invalid" : ""}`}
        aria-invalid={showError ? "true" : undefined}
        aria-describedby={describedBy}
      />

      {/* Helper text (shown when no error and no confirmation) */}
      {!showError && !showConfirm && (
        <p id={helperId} className="text-body-sm form-helper-text repo-helper">
          Public repositories only.
        </p>
      )}

      {/* Error message */}
      {showError && (
        <p
          id={errorId}
          className="text-body-sm form-error"
          role="alert"
          aria-live="polite"
        >
          {errorMessage}
        </p>
      )}

      {/* Confirmation */}
      {showConfirm && (
        <p id={confirmId} className="text-body-sm repo-confirm">
          Will scan: github.com/{parsed.owner}/{parsed.repo}
        </p>
      )}
    </div>
  );
}

RepoInput.validate = (rawValue) => parseGithubUrl(rawValue);
