// Landing Page JavaScript for Enhanced Interactions

class LandingPage {
    constructor() {
        this.init();
    }

    init() {
        this.setupParallaxEffect();
        this.setupWorkspaceCards();
        this.setupFeatureCards();
        this.createFloatingElements();
    }

    setupParallaxEffect() {
        // Add parallax scrolling effect to background elements
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const strands = document.querySelectorAll('.dna-strand');
            const particles = document.querySelectorAll('.particle');
            
            strands.forEach((strand, index) => {
                const speed = 0.5 + (index * 0.1);
                strand.style.transform += ` translateY(${scrolled * speed}px)`;
            });

            particles.forEach((particle, index) => {
                const speed = 0.3 + (index * 0.05);
                particle.style.transform += ` translateY(${scrolled * speed}px)`;
            });
        });
    }

    setupWorkspaceCards() {
        const cards = document.querySelectorAll('.workspace-card');
        
        cards.forEach(card => {
            // Add mouse move effect for 3D tilt
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                
                const deltaX = (e.clientX - centerX) / (rect.width / 2);
                const deltaY = (e.clientY - centerY) / (rect.height / 2);
                
                const rotateX = deltaY * -10; // Reduced intensity
                const rotateY = deltaX * 10;
                
                card.style.transform = `
                    translateY(-10px) 
                    rotateX(${rotateX}deg) 
                    rotateY(${rotateY}deg)
                    scale(1.02)
                `;
            });

            // Reset transform on mouse leave
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) rotateX(0) rotateY(0) scale(1)';
            });

            // Add click animation
            card.addEventListener('click', (e) => {
                // Don't animate if clicking the button directly
                if (!e.target.closest('.btn-workspace')) {
                    card.style.transform = 'scale(0.98)';
                    setTimeout(() => {
                        card.style.transform = '';
                    }, 150);
                }
            });
        });
    }

    setupFeatureCards() {
        const featureCards = document.querySelectorAll('.feature-card');
        
        // Intersection Observer for scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, index * 100);
                }
            });
        }, {
            threshold: 0.2,
            rootMargin: '0px 0px -50px 0px'
        });

        featureCards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
    }

    createFloatingElements() {
        // Create additional floating elements for enhanced visual effect
        const container = document.querySelector('.animated-background');
        
        for (let i = 0; i < 10; i++) {
            const element = document.createElement('div');
            element.className = 'floating-element';
            element.style.cssText = `
                position: absolute;
                width: 2px;
                height: 2px;
                background: rgba(13, 110, 253, 0.1);
                border-radius: 50%;
                animation: float-random 15s linear infinite;
                animation-delay: ${Math.random() * -15}s;
                top: ${Math.random() * 100}%;
                left: ${Math.random() * 100}%;
            `;
            container.appendChild(element);
        }
    }
}

// Initialize landing page effects when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new LandingPage();
});

// Add CSS animation for floating elements
const style = document.createElement('style');
style.textContent = `
    @keyframes float-random {
        0% {
            transform: translate(0, 0) scale(0);
            opacity: 0;
        }
        10% {
            opacity: 0.1;
            transform: scale(1);
        }
        90% {
            opacity: 0.1;
        }
        100% {
            transform: translate(${Math.random() * 200 - 100}px, -100vh) scale(0);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Smooth scrolling for any anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading animation for workspace cards
window.addEventListener('load', function() {
    const cards = document.querySelectorAll('.workspace-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 300 + (index * 200));
    });
});

// Initialize workspace cards with loading animation
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.workspace-card');
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
    });
});

// Performance optimization: Throttle scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Apply throttling to scroll event
const scrollHandler = throttle(function() {
    // Any scroll-based animations go here
}, 16); // ~60fps

window.addEventListener('scroll', scrollHandler);