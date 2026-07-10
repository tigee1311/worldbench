const revealElements = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const revealObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.12 }
  );
  revealElements.forEach((element) => revealObserver.observe(element));
} else {
  revealElements.forEach((element) => element.classList.add("is-visible"));
}

const shot = document.querySelector("#dashboard-shot");
const tabs = document.querySelectorAll(".tab");
const shots = {
  proof: {
    src: "/assets/screenshots/checkpoint-proof.png",
    alt: "Verified WorldBench NanoWM checkpoint proof"
  },
  terminal: {
    src: "/assets/screenshots/terminal-gate-result.png",
    alt: "Actual WorldBench terminal gate output for the NanoWM checkpoint comparison"
  }
};

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const key = tab.dataset.shot;
    const nextShot = shots[key];
    if (!nextShot || !shot) return;

    tabs.forEach((candidate) => {
      const isActive = candidate === tab;
      candidate.classList.toggle("is-active", isActive);
      candidate.setAttribute("aria-pressed", String(isActive));
    });

    shot.src = nextShot.src;
    shot.alt = nextShot.alt;
  });
});
