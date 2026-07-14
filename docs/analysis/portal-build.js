(() => {
  const renderBuild = (build) => {
    const shortCommit = String(build.commit || '').slice(0, 7);
    document.querySelectorAll('[data-portal-build="commit"]').forEach((element) => {
      element.textContent = shortCommit || 'unknown';
      if (element instanceof HTMLAnchorElement) {
        element.href = 'build.json';
        element.title = `Portal build ${build.commit}`;
      }
    });
    document.querySelectorAll('[data-portal-build="built-at"]').forEach((element) => {
      element.textContent = build.built_at || 'unknown';
    });
  };

  const loadBuild = async () => {
    try {
      const response = await fetch(new URL('build.json', document.baseURI), {
        cache: 'no-store',
      });
      if (!response.ok) {
        return;
      }
      renderBuild(await response.json());
    } catch {
      return;
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadBuild, { once: true });
  } else {
    loadBuild();
  }
})();
