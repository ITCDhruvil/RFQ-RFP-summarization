"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import { normalizeHighlightTarget } from "@/lib/citationUtils";

export interface CitationHighlightTarget {
  page: number;
  sourceText?: string;
}

interface PdfNavigationContextValue {
  activePage: number | null;
  activeHighlight: CitationHighlightTarget | null;
  flashKey: number;
  canJump: boolean;
  applyHighlight: (target: CitationHighlightTarget) => CitationHighlightTarget | null;
  jumpToCitation: (target: CitationHighlightTarget) => void;
  setCanJump: (value: boolean) => void;
  registerScrollToCitation: (fn: (target: CitationHighlightTarget) => void) => void;
  unregisterScrollToCitation: () => void;
  previewContainerRef: React.RefObject<HTMLDivElement | null>;
}

const PdfNavigationContext = createContext<PdfNavigationContextValue>({
  activePage: null,
  activeHighlight: null,
  flashKey: 0,
  canJump: false,
  applyHighlight: () => null,
  jumpToCitation: () => {},
  setCanJump: () => {},
  registerScrollToCitation: () => {},
  unregisterScrollToCitation: () => {},
  previewContainerRef: { current: null },
});

export function PdfNavigationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [activePage, setActivePage] = useState<number | null>(null);
  const [activeHighlight, setActiveHighlight] =
    useState<CitationHighlightTarget | null>(null);
  const [flashKey, setFlashKey] = useState(0);
  const [canJump, setCanJump] = useState(false);
  const previewContainerRef = useRef<HTMLDivElement | null>(null);
  const scrollToCitationRef = useRef<
    ((target: CitationHighlightTarget) => void) | null
  >(null);

  const registerScrollToCitation = useCallback(
    (fn: (target: CitationHighlightTarget) => void) => {
      scrollToCitationRef.current = fn;
    },
    []
  );

  const unregisterScrollToCitation = useCallback(() => {
    scrollToCitationRef.current = null;
  }, []);

  const applyHighlight = useCallback((target: CitationHighlightTarget) => {
    const normalized = normalizeHighlightTarget(target);
    if (!normalized) return null;
    setActivePage(normalized.page);
    setActiveHighlight(normalized);
    setFlashKey((k) => k + 1);
    return normalized;
  }, []);

  const jumpToCitation = useCallback((target: CitationHighlightTarget) => {
    const normalized = normalizeHighlightTarget(target);
    if (!normalized) return;

    previewContainerRef.current?.scrollIntoView({
      behavior: "auto",
      block: "nearest",
    });

    // Preview resolves page + applies highlight once (correct PDF page for DOCX).
    scrollToCitationRef.current?.(normalized);
  }, []);

  const value = useMemo(
    () => ({
      activePage,
      activeHighlight,
      flashKey,
      canJump,
      applyHighlight,
      jumpToCitation,
      setCanJump,
      registerScrollToCitation,
      unregisterScrollToCitation,
      previewContainerRef,
    }),
    [
      activePage,
      activeHighlight,
      flashKey,
      canJump,
      applyHighlight,
      jumpToCitation,
      registerScrollToCitation,
      unregisterScrollToCitation,
    ]
  );

  return (
    <PdfNavigationContext.Provider value={value}>
      {children}
    </PdfNavigationContext.Provider>
  );
}

export function usePdfNavigation() {
  return useContext(PdfNavigationContext);
}
