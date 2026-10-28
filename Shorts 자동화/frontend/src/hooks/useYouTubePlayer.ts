import { useCallback, useEffect, useRef, useState } from "react";

import { PLAYHEAD_POLL_MS } from "../config";
import { loadYouTubeApi, type YTPlayer } from "../lib/youtube";

/** Mounts a YouTube player into the returned ref and tracks its current time. */
export function useYouTubePlayer(videoId: string) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YTPlayer | null>(null);
  const [ready, setReady] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let player: YTPlayer | null = null;
    loadYouTubeApi().then((YT) => {
      if (cancelled || !containerRef.current) return;
      // The API replaces its element with an iframe, so give it a child React does not own.
      const mount = document.createElement("div");
      mount.className = "h-full w-full";
      containerRef.current.replaceChildren(mount);
      player = new YT.Player(mount, {
        videoId,
        playerVars: { rel: 0, modestbranding: 1 },
        events: { onReady: () => !cancelled && setReady(true) },
      });
      playerRef.current = player;
    });
    return () => {
      cancelled = true;
      player?.destroy();
      playerRef.current = null;
      setReady(false);
    };
  }, [videoId]);

  useEffect(() => {
    if (!ready) return;
    const timer = setInterval(() => {
      setCurrentTime(playerRef.current?.getCurrentTime() ?? 0);
    }, PLAYHEAD_POLL_MS);
    return () => clearInterval(timer);
  }, [ready]);

  const seek = useCallback((sec: number, play = false) => {
    playerRef.current?.seekTo(sec, true);
    if (play) playerRef.current?.playVideo();
    setCurrentTime(sec);
  }, []);

  return { containerRef, ready, currentTime, seek };
}
