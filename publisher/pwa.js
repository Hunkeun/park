/**
 * Service Worker 등록 + PWA 설치 가이드.
 * 모든 책방 페이지가 이 스크립트 한 번 include.
 */
(function () {
    if (!('serviceWorker' in navigator)) return;
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .catch((e) => console.warn('[pwa] sw 등록 실패', e));
    });

    // beforeinstallprompt — Chrome/Edge: 사용자에게 설치 권유 시점
    let deferredPrompt = null;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        // 추후 사용자가 "홈에 추가" 버튼 누르면 prompt 띄움
        window.aisbPwa = window.aisbPwa || {};
        window.aisbPwa.canInstall = true;
        window.aisbPwa.promptInstall = async () => {
            if (!deferredPrompt) return false;
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            deferredPrompt = null;
            window.aisbPwa.canInstall = false;
            return outcome === 'accepted';
        };
        window.dispatchEvent(new CustomEvent('aisbPwaInstallable'));
    });

    window.addEventListener('appinstalled', () => {
        console.log('[pwa] 설치 완료');
    });
})();
