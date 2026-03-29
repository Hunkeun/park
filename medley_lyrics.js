// Medley Playlist Data
const playlist = [
    {
        id: 'NbnlzcgiSIM',
        title: '그 겨울의 찻집',
        artist: '조용필',
        thumbnail: 'https://img.youtube.com/vi/NbnlzcgiSIM/mqdefault.jpg'
    },
    {
        id: 'w1YyyIvEQfc',
        title: '안동역에서',
        artist: '진성',
        thumbnail: 'https://img.youtube.com/vi/w1YyyIvEQfc/mqdefault.jpg'
    },
    {
        id: 'qjKO2FiTp3w',
        title: '홍시',
        artist: '나훈아',
        thumbnail: 'https://img.youtube.com/vi/qjKO2FiTp3w/mqdefault.jpg'
    },
    {
        id: 'P53SEMurUwI',
        title: '내 나이가 어때서',
        artist: '오승근',
        thumbnail: 'https://img.youtube.com/vi/P53SEMurUwI/mqdefault.jpg'
    },
    {
        id: 'siKZMFkIIwY',
        title: '신사동 그 사람',
        artist: '주현미',
        thumbnail: 'https://img.youtube.com/vi/siKZMFkIIwY/mqdefault.jpg'
    },
    {
        id: 'HDUnz4vhhKc',
        title: '동행',
        artist: '최성수',
        thumbnail: 'https://img.youtube.com/vi/HDUnz4vhhKc/mqdefault.jpg'
    },
    {
        id: 'RE2IX3s88Ds',
        title: '알고 싶어요',
        artist: '이선희',
        thumbnail: 'https://img.youtube.com/vi/RE2IX3s88Ds/mqdefault.jpg'
    },
    {
        id: 'RfI-Yv-_VJo',
        title: '부초 같은 인생',
        artist: '김용임',
        thumbnail: 'https://img.youtube.com/vi/RfI-Yv-_VJo/mqdefault.jpg'
    },
    {
        id: 'gGrIHHInevE',
        title: '막걸리 한잔',
        artist: '강진',
        thumbnail: 'https://img.youtube.com/vi/gGrIHHInevE/mqdefault.jpg'
    },
    {
        id: 'OY1xikI_8w8',
        title: '내 마음의 보석상자',
        artist: '해바라기',
        thumbnail: 'https://img.youtube.com/vi/OY1xikI_8w8/mqdefault.jpg'
    }
];

let player;
let currentTrackIndex = 0;
let isPlaying = false;
let updateTimer;

// DOM Elements
const playPauseBtn = document.getElementById('playPauseBtn');
const playIcon = document.getElementById('playIcon');
const pauseIcon = document.getElementById('pauseIcon');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const currentTitle = document.getElementById('currentTitle');
const currentArtist = document.getElementById('currentArtist');
const playlistItems = document.getElementById('playlistItems');
const progressBar = document.getElementById('progressBar');
const progressWrapper = document.getElementById('progressWrapper');
const currentTimeEl = document.getElementById('currentTime');
const durationEl = document.getElementById('duration');

// Initialize Playlist UI
function initPlaylist() {
    playlistItems.innerHTML = '';
    playlist.forEach((track, index) => {
        const li = document.createElement('li');
        li.className = `track-item ${index === currentTrackIndex ? 'active' : ''}`;
        li.innerHTML = `
            <img src="${track.thumbnail}" alt="${track.title}">
            <div class="track-item-info">
                <span class="track-item-title">${track.title}</span>
                <span class="track-item-artist">${track.artist}</span>
            </div>
        `;
        li.onclick = () => loadTrack(index);
        playlistItems.appendChild(li);
    });
}

// YT API Ready
function onYouTubeIframeAPIReady() {
    player = new YT.Player('youtube-player', {
        height: '100%',
        width: '100%',
        videoId: playlist[currentTrackIndex].id,
        playerVars: {
            'autoplay': 0,
            'controls': 0,
            'modestbranding': 1,
            'rel': 0,
            'showinfo': 0,
            'iv_load_policy': 3,
            'origin': 'http://localhost:8000'
        },
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
}

function onPlayerReady(event) {
    initPlaylist();
    updateTrackInfo();
}

function onPlayerStateChange(event) {
    if (event.data === YT.PlayerState.PLAYING) {
        isPlaying = true;
        updateUI();
        startTimer();
    } else if (event.data === YT.PlayerState.PAUSED) {
        isPlaying = false;
        updateUI();
        stopTimer();
    } else if (event.data === YT.PlayerState.ENDED) {
        nextTrack();
    }
}

function updateUI() {
    if (isPlaying) {
        playIcon.classList.add('hidden');
        pauseIcon.classList.remove('hidden');
        document.querySelector('.playing-indicator').style.display = 'flex';
    } else {
        playIcon.classList.remove('hidden');
        pauseIcon.classList.add('hidden');
        document.querySelector('.playing-indicator').style.display = 'none';
    }
}

function updateTrackInfo() {
    const track = playlist[currentTrackIndex];
    currentTitle.textContent = track.title;
    currentArtist.textContent = track.artist;
    
    // Update active state in playlist
    const items = document.querySelectorAll('.track-item');
    items.forEach((item, index) => {
        item.classList.toggle('active', index === currentTrackIndex);
    });

    // Reset progress
    progressBar.style.width = '0%';
    currentTimeEl.textContent = '0:00';
}

function loadTrack(index) {
    currentTrackIndex = index;
    player.loadVideoById(playlist[currentTrackIndex].id);
    updateTrackInfo();
}

function playPause() {
    if (isPlaying) {
        player.pauseVideo();
    } else {
        player.playVideo();
    }
}

function nextTrack() {
    currentTrackIndex = (currentTrackIndex + 1) % playlist.length;
    loadTrack(currentTrackIndex);
}

function prevTrack() {
    currentTrackIndex = (currentTrackIndex - 1 + playlist.length) % playlist.length;
    loadTrack(currentTrackIndex);
}

// Timer for Progress Bar
function startTimer() {
    updateTimer = setInterval(() => {
        if (player && player.getCurrentTime) {
            const current = player.getCurrentTime();
            const total = player.getDuration();
            if (total > 0) {
                const percent = (current / total) * 100;
                progressBar.style.width = `${percent}%`;
                document.querySelector('.progress-handle').style.left = `${percent}%`;
                
                currentTimeEl.textContent = formatTime(current);
                durationEl.textContent = formatTime(total);
            }
        }
    }, 500);
}

function stopTimer() {
    clearInterval(updateTimer);
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

// Progress Seeking
progressWrapper.onclick = (e) => {
    const rect = progressWrapper.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    const duration = player.getDuration();
    player.seekTo(pos * duration);
};

// Event Listeners
playPauseBtn.onclick = playPause;
nextBtn.onclick = nextTrack;
prevBtn.onclick = prevTrack;

// Handle potential autoplay blocking
document.body.addEventListener('click', () => {
    // Some browsers require interaction before playing
}, { once: true });
