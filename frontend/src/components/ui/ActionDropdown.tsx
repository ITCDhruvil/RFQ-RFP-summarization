"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type ActionDropdownItem =
  | {
      kind: "link";
      label: string;
      href: string;
      icon?: React.ReactNode;
      disabled?: boolean;
      description?: string;
    }
  | {
      kind: "button";
      label: string;
      onClick: () => void;
      icon?: React.ReactNode;
      disabled?: boolean;
      loading?: boolean;
      description?: string;
    };

type MenuCoords = { top: number; left: number };

function computePosition(anchor: DOMRect, menuWidth: number, menuHeight: number): MenuCoords {
  let top = anchor.bottom + 4;
  let left = anchor.right - menuWidth;
  if (top + menuHeight > window.innerHeight - 8) {
    top = Math.max(8, anchor.top - menuHeight - 4);
  }
  if (left < 8) left = 8;
  if (left + menuWidth > window.innerWidth - 8) {
    left = window.innerWidth - menuWidth - 8;
  }
  return { top, left };
}

export function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

export function ActionDropdown({
  label,
  icon,
  items,
  variant = "default",
  align = "right",
  menuWidth = 248,
}: {
  label: string;
  icon?: React.ReactNode;
  items: ActionDropdownItem[];
  variant?: "default" | "primary";
  align?: "left" | "right";
  menuWidth?: number;
}) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<MenuCoords | null>(null);
  const [mounted, setMounted] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMounted(true), []);

  const updatePosition = () => {
    const anchor = buttonRef.current?.getBoundingClientRect();
    if (!anchor) return;
    const menuHeight = menuRef.current?.offsetHeight ?? items.length * 44 + 16;
    const pos = computePosition(anchor, menuWidth, menuHeight);
    if (align === "left") {
      pos.left = anchor.left;
    }
    setCoords(pos);
  };

  useLayoutEffect(() => {
    if (!open) return;
    updatePosition();
  }, [open, items.length]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (buttonRef.current?.contains(t) || menuRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  const baseBtn =
    variant === "primary"
      ? "bg-accent text-white hover:bg-accent-hover"
      : "border border-surface-border bg-surface text-ink hover:bg-surface-muted";

  const menu =
    open && coords && mounted ? (
      <div
        ref={menuRef}
        role="menu"
        style={{ top: coords.top, left: coords.left, width: menuWidth }}
        className="fixed z-[100] rounded-lg border border-surface-border bg-surface py-1 shadow-xl"
      >
        <ul>
          {items.map((item) => (
            <li key={item.label} role="none">
              {item.kind === "link" ? (
                <Link
                  href={item.href}
                  role="menuitem"
                  onClick={() => setOpen(false)}
                  className={`flex items-start gap-2.5 px-3 py-2 text-sm transition hover:bg-surface-muted ${
                    item.disabled ? "pointer-events-none opacity-40" : "text-ink"
                  }`}
                  aria-disabled={item.disabled}
                >
                  {item.icon && (
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-muted">
                      {item.icon}
                    </span>
                  )}
                  <span>
                    <span className="font-medium">{item.label}</span>
                    {item.description && (
                      <span className="mt-0.5 block text-xs text-ink-muted">
                        {item.description}
                      </span>
                    )}
                  </span>
                </Link>
              ) : (
                <button
                  type="button"
                  role="menuitem"
                  disabled={item.disabled || item.loading}
                  onClick={() => {
                    if (item.disabled || item.loading) return;
                    item.onClick();
                    setOpen(false);
                  }}
                  className={`flex w-full items-start gap-2.5 px-3 py-2 text-left text-sm transition hover:bg-surface-muted disabled:opacity-40 ${
                    item.disabled ? "" : "text-ink"
                  }`}
                >
                  {item.icon && (
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-muted">
                      {item.icon}
                    </span>
                  )}
                  <span>
                    <span className="font-medium">
                      {item.loading ? "Preparing…" : item.label}
                    </span>
                    {item.description && (
                      <span className="mt-0.5 block text-xs text-ink-muted">
                        {item.description}
                      </span>
                    )}
                  </span>
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    ) : null;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${baseBtn}`}
      >
        {icon}
        <span>{label}</span>
        <ChevronDownIcon className="opacity-60" />
      </button>
      {mounted && menu ? createPortal(menu, document.body) : null}
    </>
  );
}
