"use client";
import { createContext, useCallback, useContext, useEffect, useState, useRef, ReactNode } from "react";
import { usePathname } from "next/navigation";
import { LOADING_SHOW, LOADING_HIDE } from "@/lib/api";

interface LoadingCtx {
  loading: boolean;
  show: () => void;
  hide: () => void;
}

const LoadingCtx = createContext<LoadingCtx>({
  loading: false,
  show: () => {},
  hide: () => {},
});

export function useLoading() {
  return useContext(LoadingCtx);
}

export function LoadingProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const countRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pathname = usePathname();
  const prevPathRef = useRef(pathname);

  const show = useCallback(() => {
    countRef.current++;
    if (timerRef.current) clearTimeout(timerRef.current);
    setLoading(true);
    setProgress(0);
    
    // Animate progress
    if (progressRef.current) clearInterval(progressRef.current);
    let currentProgress = 0;
    progressRef.current = setInterval(() => {
      currentProgress += Math.random() * 15;
      if (currentProgress >= 90) {
        currentProgress = 90;
        if (progressRef.current) clearInterval(progressRef.current);
      }
      setProgress(currentProgress);
    }, 100);
    
    // Auto-hide after timeout
    timerRef.current = setTimeout(() => {
      countRef.current = 0;
      setLoading(false);
      setProgress(0);
      if (progressRef.current) clearInterval(progressRef.current);
    }, 8000);
  }, []);

  const hide = useCallback(() => {
    countRef.current = Math.max(0, countRef.current - 1);
    if (countRef.current === 0) {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (progressRef.current) clearInterval(progressRef.current);
      // Complete the progress bar before hiding
      setProgress(100);
      setTimeout(() => {
        setLoading(false);
        setProgress(0);
      }, 200);
    }
  }, []);

  // Listen to API loading events
  useEffect(() => {
    const onShow = () => show();
    const onHide = () => hide();
    window.addEventListener(LOADING_SHOW, onShow);
    window.addEventListener(LOADING_HIDE, onHide);
    return () => {
      window.removeEventListener(LOADING_SHOW, onShow);
      window.removeEventListener(LOADING_HIDE, onHide);
    };
  }, [show, hide]);

  // Auto-show on route changes with progress animation
  useEffect(() => {
    if (prevPathRef.current !== pathname) {
      prevPathRef.current = pathname;
      setLoading(true);
      setProgress(0);
      
      // Animate progress during route change
      let currentProgress = 0;
      if (progressRef.current) clearInterval(progressRef.current);
      progressRef.current = setInterval(() => {
        currentProgress += Math.random() * 20;
        if (currentProgress >= 95) {
          currentProgress = 95;
          if (progressRef.current) clearInterval(progressRef.current);
        }
        setProgress(currentProgress);
      }, 50);
      
      const t = setTimeout(() => {
        if (progressRef.current) clearInterval(progressRef.current);
        setProgress(100);
        setTimeout(() => {
          setLoading(false);
          setProgress(0);
        }, 150);
      }, 350);
      return () => {
        clearTimeout(t);
        if (progressRef.current) clearInterval(progressRef.current);
      };
    }
  }, [pathname]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (progressRef.current) clearInterval(progressRef.current);
    };
  }, []);

  return (
    <LoadingCtx.Provider value={{ loading, show, hide }}>
      {children}
      {loading && (
        <div className="loading-overlay" role="status" aria-label="Loading">
          {/* Progress bar at top */}
          <div 
            className="fixed top-0 left-0 right-0 h-1 z-[10000]"
            style={{ background: "transparent" }}
          >
            <div
              className="h-full transition-all duration-200 ease-out"
              style={{
                width: `${progress}%`,
                background: "var(--brand-grad)",
                boxShadow: progress > 0 ? "0 0 10px var(--primary)" : "none",
              }}
            />
          </div>
          
          {/* Loading spinner and text */}
          <div className="loading-overlay__spinner" />
          <div className="loading-overlay__text">
            <span>Loading</span>
            <span className="copilot-dot">.</span>
            <span className="copilot-dot">.</span>
            <span className="copilot-dot">.</span>
          </div>
          
          {/* Progress percentage */}
          {progress > 0 && progress < 100 && (
            <div className="mt-3 text-[11px] font-medium" style={{ color: "var(--muted)" }}>
              {Math.round(progress)}%
            </div>
          )}
        </div>
      )}
    </LoadingCtx.Provider>
  );
}
