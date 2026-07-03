"use client";

import { useEffect } from "react";

function isChunkLoadError(error: Error) {
  return (
    error.name === "ChunkLoadError" ||
    error.message.includes("Loading chunk")
  );
}

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const chunkError = isChunkLoadError(error);

  useEffect(() => {
    if (!chunkError) return;

    const key = "next-chunk-reload";
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, "1");
      window.location.reload();
      return;
    }

    sessionStorage.removeItem(key);
  }, [chunkError]);

  if (chunkError) {
    return (
      <html lang="en">
        <body>
          <p>Refreshing after a stale build cache…</p>
        </body>
      </html>
    );
  }

  return (
    <html lang="en">
      <body>
        <h2>Something went wrong</h2>
        <button type="button" onClick={() => reset()}>
          Try again
        </button>
      </body>
    </html>
  );
}
