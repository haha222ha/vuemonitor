import { ref, onMounted, onUnmounted } from "vue";

interface LazyImageOptions {
  rootMargin?: string;
  threshold?: number;
  placeholder?: string;
}

export function useLazyImage(src: string, options: LazyImageOptions = {}) {
  const {
    rootMargin = "50px",
    threshold = 0.01,
    placeholder = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3C/svg%3E",
  } = options;

  const imageSrc = ref(placeholder);
  const isLoading = ref(false);
  const isLoaded = ref(false);
  const hasError = ref(false);

  let observer: IntersectionObserver | null = null;
  let imgElement: HTMLImageElement | null = null;

  function loadImage() {
    if (!src || isLoaded.value) return;

    isLoading.value = true;
    imgElement = new Image();

    imgElement.onload = () => {
      imageSrc.value = src;
      isLoaded.value = true;
      isLoading.value = false;
      hasError.value = false;
      observer?.disconnect();
    };

    imgElement.onerror = () => {
      hasError.value = true;
      isLoading.value = false;
      observer?.disconnect();
    };

    imgElement.src = src;
  }

  onMounted(() => {
    if ("IntersectionObserver" in window) {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            loadImage();
          }
        },
        { rootMargin, threshold }
      );

      const el = document.querySelector(`[data-lazy-src="${src}"]`);
      if (el) observer.observe(el);
    } else {
      loadImage();
    }
  });

  onUnmounted(() => {
    observer?.disconnect();
    imgElement = null;
  });

  return {
    imageSrc,
    isLoading,
    isLoaded,
    hasError,
    loadImage,
  };
}
