// =============================
// 🎥 films.js — Interactive Logic for Film UI (2025)
// =============================

// 📌 Sample film data
const films = [
    {
        title: "Inception",
        year: 2010,
        genre: ["Action", "Sci-Fi"],
        poster: "inception.jpg",
        trailer: "inception-trailer.mp4"
    },
    {
        title: "The Matrix",
        year: 1999,
        genre: ["Action", "Sci-Fi"],
        poster: "matrix.jpg",
        trailer: "matrix-trailer.mp4"
    },
    {
        title: "Interstellar",
        year: 2014,
        genre: ["Adventure", "Drama", "Sci-Fi"],
        poster: "interstellar.jpg",
        trailer: "interstellar-trailer.mp4"
    }
];

// 🛠️ Render films grid
document.addEventListener('DOMContentLoaded', () => {
    const grid = document.querySelector('.films-grid');

    films.forEach(film => {
        const card = document.createElement('div');
        card.className = 'card';

        card.innerHTML = `
            <div class="card-img-wrapper">
                <img src="${film.poster}" alt="${film.title}" class="card-img-top">
                <div class="card-img-overlay"></div>
            </div>
            <div class="video-info">
                <h3>${film.title}</h3>
                <p>${film.genre.join(', ')} | ${film.year}</p>
                <button class="btn play-btn" data-trailer="${film.trailer}">▶️ Watch Trailer</button>
            </div>
        `;

        grid.appendChild(card);
    });

    // 🎬 Trailer modal logic
    document.body.addEventListener('click', (e) => {
        if (e.target.classList.contains('play-btn')) {
            const trailerSrc = e.target.getAttribute('data-trailer');
            openTrailerModal(trailerSrc);
        }
    });
});

// 🌌 Trailer Modal Function
function openTrailerModal(src) {
    const modalHtml = `
        <div class="trailer-modal">
            <div class="modal-content">
                <video controls autoplay>
                    <source src="${src}" type="video/mp4">
                </video>
                <button class="btn close-btn">❌ Close</button>
            </div>
        </div>
    `;

    const modal = document.createElement('div');
    modal.innerHTML = modalHtml;
    document.body.appendChild(modal);

    modal.querySelector('.close-btn').addEventListener('click', () => {
        modal.remove();
    });
}

// ✨ Optional: Lazy load images (2025 Modern)
if ('IntersectionObserver' in window) {
    const lazyImages = document.querySelectorAll('img');
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.getAttribute('src');
                observer.unobserve(img);
            }
        });
    });

    lazyImages.forEach(img => {
        observer.observe(img);
    });
}

console.log('🎥 films.js loaded — Ready to showcase films!');
