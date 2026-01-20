import { ReactNode, useEffect } from 'react';
import { createPortal } from 'react-dom';
import type { MouseEvent } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  ariaLabel?: string;
}

export function Modal({ open, onClose, children, ariaLabel }: ModalProps): JSX.Element | null {
  useEffect(() => {
    if (!open || typeof document === 'undefined') {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onClose]);

  if (!open || typeof document === 'undefined') {
    return null;
  }

  const handleContentClick = (event: MouseEvent<HTMLDivElement>) => {
    event.stopPropagation();
  };

  const content = (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      onClick={onClose}
    >
      <div className="modal" onClick={handleContentClick}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close dialog">
          ×
        </button>
        {children}
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
