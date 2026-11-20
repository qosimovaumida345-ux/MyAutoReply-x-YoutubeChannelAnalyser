let lottiePromise = null;
let confettiPromise = null;

export function loadLottiePlayer() {
  if (typeof window === 'undefined') return Promise.resolve();
  if (window.customElements?.get('lottie-player')) return Promise.resolve();
  if (lottiePromise) return lottiePromise;
  lottiePromise = new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
  return lottiePromise;
}

export function loadConfetti() {
  if (typeof window === 'undefined') return Promise.resolve();
  if (typeof window.confetti === 'function') return Promise.resolve();
  if (confettiPromise) return confettiPromise;
  confettiPromise = new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
  return confettiPromise;
}
