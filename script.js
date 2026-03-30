// Initial voting data
// In a real app, this would come from a server
let votes = {
    bibimbap: 0,
    donkatsu: 0,
    gukbap: 0,
    salad: 0
};

let currentSelection = null;
let hasVoted = false;

/**
 * Handles selecting a menu card
 * @param {string} menu - The menu identifier
 */
function selectMenu(menu) {
    // Selection is allowed anytime before clicking vote

    // Remove selected class from all cards
    document.querySelectorAll('.menu-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Add selected class to the clicked card
    const selectedCard = document.getElementById(`card-${menu}`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
        currentSelection = menu;

        // Enable button
        document.getElementById('vote-button').disabled = false;
    }
}

// Google Apps Script Web App URL (투표 결과를 저장하기 위한 주소)
// 추후 이 주소를 실제 배포한 앱스 스크립트 URL로 바꾸셔야 합니다.
const SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxKLdJxmzDJJVGGRKim-absz7Dx-gD3Ab5qs0UrJTczxyFvj2e-qPMhVIBXBzz2k81E/exec';

/**
 * Casts a vote for the selected menu
 */
async function castVote() {
    if (!currentSelection) return;

    const votedMenu = currentSelection; // 현재 선택된 메뉴

    // Show quick feedback and disable button immediately to prevent spam
    const voteButton = document.getElementById('vote-button');
    const originalText = voteButton.textContent;
    voteButton.textContent = "투표 처리 중...";
    voteButton.disabled = true;

    try {
        // 구글 시트에 데이터 저장 (비동기로 요청)
        // CORS 문제를 피하기 위해 GET 방식의 JSONP나 단순 GET 사용 (설정된 SCRIPT_URL 활용)
        if (SCRIPT_URL.includes("macros/s/")) {
            await fetch(`${SCRIPT_URL}?menu=${encodeURIComponent(votedMenu)}`, {
                method: 'GET',
                mode: 'no-cors' // Google Script로 보낼 때 브라우저 CORS 차단 우회
            });
        }
    } catch (e) {
        console.error("투표 저장 중 에러 발생:", e);
    }

    // Update local state temporarily for immediate UI response
    votes[votedMenu]++;

    voteButton.textContent = "투표되었습니다!";
    voteButton.classList.add('success-flash');

    // Reveal and update results
    renderResults();

    const resultsPanel = document.getElementById('results-panel');
    resultsPanel.classList.remove('hidden');

    // Reset selection for next voter after a short delay
    setTimeout(() => {
        voteButton.textContent = originalText;
        voteButton.classList.remove('success-flash');

        // Clear selection visual
        document.querySelectorAll('.menu-card').forEach(card => card.classList.remove('selected'));
        currentSelection = null;
        // Keep button disabled until next selection
        voteButton.disabled = true;
    }, 1500);
}

/**
 * Calculates and renders voting results
 */
function renderResults() {
    const container = document.getElementById('results-container');
    const totalVotesDisplay = document.getElementById('total-votes');

    // Calculate total
    const total = Object.values(votes).reduce((acc, val) => acc + val, 0);
    totalVotesDisplay.textContent = total;

    // Clear and redraw container
    container.innerHTML = '';

    const menuDisplayNames = {
        bibimbap: '비빔밥',
        donkatsu: '돈까스',
        gukbap: '국밥',
        salad: '샐러드'
    };

    // Sorted results - show highest votes first? Maybe keep original order for consistency
    Object.keys(votes).forEach(key => {
        const voteCount = votes[key];
        const percentage = total > 0 ? (voteCount / total * 100).toFixed(1) : 0;

        const resultItem = document.createElement('div');
        resultItem.className = 'result-item';

        resultItem.innerHTML = `
            <div class="result-label">
                <span>${menuDisplayNames[key]}</span>
                <span>${voteCount}표 (${percentage}%)</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progress-${key}"></div>
            </div>
        `;

        container.appendChild(resultItem);

        // Animate progress bar in next frame
        setTimeout(() => {
            const fill = document.getElementById(`progress-${key}`);
            if (fill) fill.style.width = `${percentage}%`;
        }, 50);
    });
}

/**
 * Normalizes menu name for matching
 */
function normalizeMenu(name) {
    if (!name) return '';
    return String(name).trim().replace(/\s+/g, '').toLowerCase();
}

/**
 * [Best Practice] Fetches and parses JSON data directly from Google Apps Script
 * - Uses a single backend endpoint to avoid 3rd party proxies (CORS issues resolved natively by Apps Script)
 * - Expects JSON format rather than fragile CSV parsing
 */
async function loadSheetData() {
    try {
        // If the URL isn't configured yet, fallback gracefully
        if (!SCRIPT_URL.includes("macros/s/")) {
            console.log("스크립트 URL이 설정되지 않아 초기 상태 0표로 노출됩니다.");
            return renderResults();
        }

        // action=getData 파라미터를 추가해 서버에 데이터 요청
        const response = await fetch(`${SCRIPT_URL}?action=getData`);
        if (!response.ok) throw new Error('Sheet data fetch failed');

        const data = await response.json();

        // 데이터 초기화
        let newVotes = {
            bibimbap: 0,
            donkatsu: 0,
            gukbap: 0,
            salad: 0
        };

        // 안전한 데이터 순회 및 집계
        if (data && Array.isArray(data.items)) {
            data.items.forEach(row => {
                const rawMenu = normalizeMenu(row.menu);
                if (rawMenu.includes('비빔밥') || rawMenu.includes('bibimbap')) newVotes.bibimbap++;
                else if (rawMenu.includes('돈까스') || rawMenu.includes('돈까지') || rawMenu.includes('donkatsu')) newVotes.donkatsu++;
                else if (rawMenu.includes('국밥') || rawMenu.includes('gukbap')) newVotes.gukbap++;
                else if (rawMenu.includes('샐러드') || rawMenu.includes('salad')) newVotes.salad++;
            });
        }

        votes = newVotes;
        renderResults();

        const total = Object.values(votes).reduce((acc, val) => acc + val, 0);
        if (total > 0) {
            document.getElementById('results-panel').classList.remove('hidden');
        }

    } catch (error) {
        console.error('API Load Error:', error);
        renderResults();
    }
}

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('vote-button').disabled = true;

    // Load initial data securely
    loadSheetData();
});
