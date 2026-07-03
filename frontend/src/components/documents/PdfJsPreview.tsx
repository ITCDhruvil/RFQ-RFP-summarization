"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
import type { RenderTask } from "pdfjs-dist/types/src/display/api";
import type { PageViewport } from "pdfjs-dist/types/src/display/display_utils";
import * as pdfjs from "pdfjs-dist";

import { normalizeCitationPage } from "@/lib/citationUtils";
import type { CitationHighlightTarget } from "@/lib/pdfNavigationContext";
import { resolveCitationInPdf } from "@/lib/citationPdfNavigation";
import { findHighlightRects, type ViewportRect } from "@/lib/pdfTextHighlight";
import { normalizeHighlightTarget } from "@/lib/citationUtils";
import { usePdfNavigation } from "@/lib/pdfNavigationContext";

if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

const RENDER_SCALE = 1.25;
const SCROLL_PADDING_PX = 12;

function isRenderCancelledError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const name = (error as { name?: string }).name ?? "";
  return name === "RenderingCancelledException" || name === "AbortException";
}

interface PdfJsPreviewProps {
  fileUrl: string;
  activeHighlight: CitationHighlightTarget | null;
  flashKey: number;
  onReady?: () => void;
  onLoadFailed?: () => void;
  onRegisterNavigator: (fn: (target: CitationHighlightTarget) => void) => void;
  onUnregisterNavigator: () => void;
  wrapperRef?: React.RefObject<HTMLDivElement | null>;
  /** Shown when the PDF cannot be loaded (e.g. DOCX conversion not configured). */
  unavailableMessage?: string;
}

function scrollPageIntoContainer(
  container: HTMLDivElement,
  pageEl: HTMLElement,
  instant = true
) {
  const containerTop = container.getBoundingClientRect().top;
  const pageTop = pageEl.getBoundingClientRect().top;
  const nextTop =
    container.scrollTop + (pageTop - containerTop) - SCROLL_PADDING_PX;

  container.scrollTo({
    top: Math.max(0, nextTop),
    behavior: instant ? "auto" : "smooth",
  });
}

function scrollHighlightIntoContainer(
  container: HTMLDivElement,
  highlightEl: HTMLElement,
  instant = true
) {
  const containerTop = container.getBoundingClientRect().top;
  const highlightTop = highlightEl.getBoundingClientRect().top;
  const nextTop =
    container.scrollTop + (highlightTop - containerTop) - SCROLL_PADDING_PX * 3;

  container.scrollTo({
    top: Math.max(0, nextTop),
    behavior: instant ? "auto" : "smooth",
  });
}

function PdfPageCanvas({
  doc,
  pageNumber,
  pageHighlighted,
  highlightSourceText,
  highlightRevision,
  scrollContainerRef,
  onRendered,
}: {
  doc: PDFDocumentProxy;
  pageNumber: number;
  pageHighlighted: boolean;
  highlightSourceText?: string;
  highlightRevision?: number;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  onRendered: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const renderTaskRef = useRef<RenderTask | null>(null);
  const pageRef = useRef<PDFPageProxy | null>(null);
  const viewportRef = useRef<PageViewport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highlightRects, setHighlightRects] = useState<ViewportRect[]>([]);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [pageReady, setPageReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setPageReady(false);
    setError(null);
    setHighlightRects([]);

    async function renderPage() {
      renderTaskRef.current?.cancel();
      renderTaskRef.current = null;
      pageRef.current = null;
      viewportRef.current = null;

      try {
        const page = await doc.getPage(pageNumber);
        if (cancelled) return;

        const viewport = page.getViewport({ scale: RENDER_SCALE });
        const canvas = canvasRef.current;
        if (!canvas || cancelled) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        setViewportSize({ width: viewport.width, height: viewport.height });

        const task = page.render({ canvasContext: ctx, viewport, canvas });
        renderTaskRef.current = task;
        await task.promise;

        if (cancelled) return;

        pageRef.current = page;
        viewportRef.current = viewport;
        setPageReady(true);
        onRendered();
      } catch (e) {
        if (cancelled || isRenderCancelledError(e)) return;
        setError(e instanceof Error ? e.message : "Failed to render page");
        setHighlightRects([]);
        onRendered();
      }
    }

    void renderPage();
    return () => {
      cancelled = true;
      renderTaskRef.current?.cancel();
      renderTaskRef.current = null;
    };
  }, [doc, pageNumber, onRendered]);

  useEffect(() => {
    if (!pageReady) return;

    let cancelled = false;

    async function updateHighlights() {
      const page = pageRef.current;
      const viewport = viewportRef.current;
      if (!page || !viewport) return;

      if (!highlightSourceText?.trim()) {
        if (!cancelled) setHighlightRects([]);
        return;
      }

      try {
        const rects = await findHighlightRects(
          page,
          viewport,
          highlightSourceText
        );
        if (!cancelled) setHighlightRects(rects);
      } catch {
        if (!cancelled) setHighlightRects([]);
      }
    }

    void updateHighlights();
    return () => {
      cancelled = true;
    };
  }, [pageReady, highlightSourceText, highlightRevision]);

  useEffect(() => {
    if (!highlightRects.length) return;
    const container = scrollContainerRef.current;
    const firstMark = overlayRef.current?.querySelector("[data-highlight]");
    if (!container || !firstMark) return;

    const id = requestAnimationFrame(() => {
      scrollHighlightIntoContainer(container, firstMark as HTMLElement);
    });
    return () => cancelAnimationFrame(id);
  }, [highlightRects, scrollContainerRef]);

  return (
    <div
      className={`relative rounded border bg-white shadow-sm transition-shadow duration-300 ${
        pageHighlighted
          ? "border-accent ring-2 ring-accent/40 ring-offset-2"
          : "border-surface-border"
      }`}
    >
      {error ? (
        <p className="p-4 text-xs text-red-600">Page {pageNumber}: {error}</p>
      ) : (
        <div className="relative mx-auto" style={{ width: viewportSize.width || "100%" }}>
          <canvas ref={canvasRef} className="mx-auto block max-w-full" />
          {highlightRects.length > 0 && viewportSize.width > 0 && (
            <div
              ref={overlayRef}
              className="pointer-events-none absolute inset-0"
              style={{
                width: viewportSize.width,
                height: viewportSize.height,
              }}
            >
              {highlightRects.map((rect, i) => (
                <div
                  key={i}
                  data-highlight
                  className="absolute rounded-sm bg-amber-300/70 ring-2 ring-amber-500/80"
                  style={{
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height,
                  }}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function PdfJsPreview({
  fileUrl,
  activeHighlight,
  flashKey,
  onReady,
  onLoadFailed,
  onRegisterNavigator,
  onUnregisterNavigator,
  wrapperRef,
  unavailableMessage,
}: PdfJsPreviewProps) {
  const { applyHighlight } = usePdfNavigation();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const jumpScrollTokenRef = useRef(0);
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [renderedPages, setRenderedPages] = useState<Set<number>>(() => new Set([1]));
  const [pendingScroll, setPendingScroll] = useState<CitationHighlightTarget | null>(
    null
  );
  const [renderGeneration, setRenderGeneration] = useState(0);

  const ensurePagesAround = useCallback((page: number, total: number) => {
    setRenderedPages((prev) => {
      const next = new Set(prev);
      for (let p = Math.max(1, page - 1); p <= Math.min(total, page + 1); p++) {
        next.add(p);
      }
      return next;
    });
  }, []);

  const primePagesForJump = useCallback((page: number, total: number) => {
    setRenderedPages((prev) => {
      const next = new Set(prev);
      next.add(page);
      if (page > 1) next.add(page - 1);
      if (page < total) next.add(page + 1);
      return next;
    });
  }, []);

  const tryScrollToPending = useCallback(() => {
    const target = pendingScroll;
    const container = scrollRef.current;
    if (!target || !container) return;

    const pageEl = pageRefs.current.get(target.page);
    if (!pageEl) return;
    if (!pageEl.querySelector("canvas")) return;

    scrollPageIntoContainer(container, pageEl, true);
    setPendingScroll(null);
  }, [pendingScroll]);

  const scrollToCitation = useCallback(
    (target: CitationHighlightTarget) => {
      const normalized = normalizeHighlightTarget(target);
      if (!normalized || !doc) return;

      const jumpToken = ++jumpScrollTokenRef.current;

      void (async () => {
        const total = doc.numPages;
        let page = Math.min(Math.max(1, normalized.page), total);
        let sourceText = normalized.sourceText;

        if (sourceText?.trim()) {
          const located = await resolveCitationInPdf(
            doc,
            page,
            sourceText,
            RENDER_SCALE
          );
          if (jumpToken !== jumpScrollTokenRef.current) return;
          if (located) {
            page = located.page;
          }
        }

        const resolved = applyHighlight({ page, sourceText });
        if (!resolved || jumpToken !== jumpScrollTokenRef.current) return;

        page = resolved.page;
        sourceText = resolved.sourceText;

        primePagesForJump(page, total);
        ensurePagesAround(page, total);
        setPendingScroll({ page, sourceText });
      })();
    },
    [doc, applyHighlight, ensurePagesAround, primePagesForJump]
  );

  useEffect(() => {
    onRegisterNavigator(scrollToCitation);
    return () => onUnregisterNavigator();
  }, [scrollToCitation, onRegisterNavigator, onUnregisterNavigator]);

  useEffect(() => {
    if (!pendingScroll) return;
    const id = requestAnimationFrame(() => {
      requestAnimationFrame(() => tryScrollToPending());
    });
    return () => cancelAnimationFrame(id);
  }, [pendingScroll, renderedPages, renderGeneration, tryScrollToPending]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container || numPages === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let changed = false;
        const toAdd: number[] = [];

        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const pageAttr = (entry.target as HTMLElement).dataset.page;
          const pageNum = pageAttr ? Number(pageAttr) : NaN;
          if (!Number.isFinite(pageNum)) continue;
          toAdd.push(pageNum);
          changed = true;
        }

        if (!changed) return;

        setRenderedPages((prev) => {
          const merged = new Set(prev);
          for (const p of toAdd) {
            merged.add(p);
            if (p > 1) merged.add(p - 1);
            if (p < numPages) merged.add(p + 1);
          }
          return merged;
        });
      },
      { root: container, rootMargin: "240px 0px", threshold: 0.01 }
    );

    const id = requestAnimationFrame(() => {
      for (const el of pageRefs.current.values()) {
        observer.observe(el);
      }
    });

    return () => {
      cancelAnimationFrame(id);
      observer.disconnect();
    };
  }, [numPages, doc]);

  useEffect(() => {
    let cancelled = false;
    let loadedDoc: PDFDocumentProxy | null = null;

    async function load() {
      setDoc(null);
      setNumPages(0);
      setLoadError(null);
      setRenderedPages(new Set([1]));
      setPendingScroll(null);

      try {
        const task = pdfjs.getDocument({ url: fileUrl, withCredentials: false });
        loadedDoc = await task.promise;
        if (cancelled) {
          void loadedDoc.destroy();
          return;
        }
        setDoc(loadedDoc);
        setNumPages(loadedDoc.numPages);
        onReady?.();
      } catch (e) {
        if (!cancelled) {
          setLoadError(
            e instanceof Error ? e.message : "Could not load PDF for preview"
          );
          onLoadFailed?.();
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
      if (loadedDoc) void loadedDoc.destroy();
    };
  }, [fileUrl, onReady, onLoadFailed]);

  const handlePageRendered = useCallback(() => {
    setRenderGeneration((g) => g + 1);
  }, []);

  if (loadError) {
    return (
      <div className="flex h-full min-h-0 flex-1 items-center justify-center rounded-md border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
        {unavailableMessage ?? loadError}
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="flex h-full min-h-0 flex-1 items-center justify-center rounded-md border border-surface-border bg-surface">
        <p className="text-sm text-ink-muted">Loading PDF preview…</p>
      </div>
    );
  }

  return (
    <div
      ref={wrapperRef}
      className="flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-surface-border bg-surface-muted/40"
    >
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3"
      >
        <div className="mx-auto flex max-w-full flex-col gap-4">
          {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => {
            const shouldRender = renderedPages.has(pageNum);
            const highlightPage = normalizeCitationPage(activeHighlight?.page);
            const isPageHighlighted = highlightPage === pageNum;
            const textForPage =
              highlightPage === pageNum
                ? activeHighlight?.sourceText
                : undefined;

            return (
              <div
                key={pageNum}
                ref={(el) => {
                  if (el) pageRefs.current.set(pageNum, el);
                  else pageRefs.current.delete(pageNum);
                }}
                data-page={pageNum}
                className="scroll-mt-3"
              >
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink-muted">
                  Page {pageNum}
                </p>
                {shouldRender ? (
                  <PdfPageCanvas
                    doc={doc}
                    pageNumber={pageNum}
                    pageHighlighted={isPageHighlighted}
                    highlightSourceText={textForPage}
                    highlightRevision={flashKey}
                    scrollContainerRef={scrollRef}
                    onRendered={handlePageRendered}
                  />
                ) : (
                  <div className="flex h-40 items-center justify-center rounded border border-dashed border-surface-border bg-surface text-xs text-ink-muted">
                    Scroll to load page {pageNum}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
