// ApexCart - Target Store Client Logic
const PRODUCTS = [
    { id: 1, title: "Noise-Cancelling Wireless Headphones", category: "audio", price: 99.99, icon: "🎧", desc: "Premium acoustic drivers with active 40dB ambient cancellation." },
    { id: 2, title: "Quantum Fitness Smart Watch", category: "wearables", price: 149.50, icon: "⌚", desc: "AMOLED biometric tracker with continuous ECG & SpO2 monitoring." },
    { id: 3, title: "Ergonomic Mechanical Keyboard", category: "accessories", price: 79.00, icon: "⌨️", desc: "Hot-swappable linear switches with customizable RGB lighting." },
    { id: 4, title: "Ultra-Fast Wireless Charging Dock", category: "accessories", price: 39.99, icon: "⚡", desc: "15W Qi-certified dual station for phone and earbuds." },
    { id: 5, title: "Studio Hi-Fi Bluetooth Speaker", category: "audio", price: 119.00, icon: "🔊", desc: "360-degree room-filling sound with 24-hour battery reserve." },
    { id: 6, title: "Pro Gaming Optical Mouse", category: "accessories", price: 49.99, icon: "🖱️", desc: "26,000 DPI sensor with sub-millisecond wireless latency." }
];

let cart = [];
let appliedDiscount = 0.0;
let userSession = null;

// DOM Elements
const productGrid = document.getElementById("product-grid");
const noResultsMsg = document.getElementById("no-results-msg");
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const catPills = document.querySelectorAll(".cat-pill");

const navLoginBtn = document.getElementById("nav-login-btn");
const userProfileBadge = document.getElementById("user-profile-badge");
const userDisplayName = document.getElementById("user-display-name");
const logoutBtn = document.getElementById("logout-btn");
const loginModal = document.getElementById("login-modal");
const closeLoginBtn = document.getElementById("close-login-btn");
const cancelLoginBtn = document.getElementById("cancel-login-btn");
const loginForm = document.getElementById("login-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginErrorAlert = document.getElementById("login-error-alert");
const emailError = document.getElementById("email-error");
const passwordError = document.getElementById("password-error");

const cartIconBtn = document.getElementById("cart-icon-btn");
const cartBadgeCount = document.getElementById("cart-badge-count");
const checkoutModal = document.getElementById("checkout-modal");
const closeCheckoutBtn = document.getElementById("close-checkout-btn");
const cancelCheckoutBtn = document.getElementById("cancel-checkout-btn");
const cartItemsList = document.getElementById("cart-items-list");
const promoInput = document.getElementById("promo-input");
const applyPromoBtn = document.getElementById("apply-promo-btn");
const discountBadge = document.getElementById("discount-badge");
const discountAmount = document.getElementById("discount-amount");
const orderSubtotalPrice = document.getElementById("order-subtotal-price");
const orderDiscountDisplay = document.getElementById("order-discount-display");
const orderTotalPrice = document.getElementById("order-total-price");
const checkoutBtn = document.getElementById("checkout-btn");
const orderSuccessBanner = document.getElementById("order-success-banner");
const confirmedOrderId = document.getElementById("confirmed-order-id");
const bugModeToggle = document.getElementById("bug-mode-toggle");

// Render Products
function renderProducts(items) {
    productGrid.innerHTML = "";
    if (items.length === 0) {
        noResultsMsg.style.display = "block";
        return;
    }
    noResultsMsg.style.display = "none";

    items.forEach(p => {
        const card = document.createElement("div");
        card.className = "product-card";
        card.innerHTML = `
            <div>
                <div class="product-icon">${p.icon}</div>
                <h4 class="product-title">${p.title}</h4>
                <p class="product-desc">${p.desc}</p>
            </div>
            <div class="product-footer">
                <span class="product-price">$${p.price.toFixed(2)}</span>
                <button class="add-to-cart-btn" data-id="${p.id}">+ Add to Cart</button>
            </div>
        `;
        productGrid.appendChild(card);
    });

    // Attach Add to Cart Listeners
    document.querySelectorAll(".add-to-cart-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const pid = parseInt(btn.getAttribute("data-id"));
            addToCart(pid);
        });
    });
}

// Filter and Search
function filterProducts() {
    const query = searchInput.value.trim().toLowerCase();
    const activeCat = document.querySelector(".cat-pill.active")?.getAttribute("data-cat") || "all";

    const filtered = PRODUCTS.filter(p => {
        const matchesQuery = query === "" || p.title.toLowerCase().includes(query) || p.desc.toLowerCase().includes(query);
        const matchesCat = activeCat === "all" || p.category === activeCat;
        return matchesQuery && matchesCat;
    });

    renderProducts(filtered);
}

searchBtn.addEventListener("click", filterProducts);
searchInput.addEventListener("keyup", (e) => {
    if (e.key === "Enter") filterProducts();
});

catPills.forEach(pill => {
    pill.addEventListener("click", () => {
        catPills.forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        filterProducts();
    });
});

// Cart Management
function addToCart(productId) {
    const prod = PRODUCTS.find(p => p.id === productId);
    if (!prod) return;
    cart.push(prod);
    updateCartUI();
}

function updateCartUI() {
    cartBadgeCount.textContent = cart.length;
    updateCheckoutSummary();
}

function updateCheckoutSummary() {
    const subtotal = cart.reduce((sum, item) => sum + item.price, 0);
    orderSubtotalPrice.textContent = `$${subtotal.toFixed(2)}`;

    // Calculate discount
    const isBugMode = bugModeToggle && bugModeToggle.checked;
    let discountVal = 0.0;

    if (appliedDiscount > 0) {
        if (isBugMode) {
            // Intentionally don't deduct discount in bug mode for testing failure detection!
            discountVal = 0.0;
        } else {
            discountVal = subtotal * appliedDiscount;
        }
    }

    const grandTotal = Math.max(0, subtotal - discountVal);
    orderDiscountDisplay.textContent = `-$${discountVal.toFixed(2)}`;
    orderTotalPrice.textContent = `$${grandTotal.toFixed(2)}`;
    discountAmount.textContent = discountVal.toFixed(2);
}

function renderCartItems() {
    cartItemsList.innerHTML = "";
    if (cart.length === 0) {
        cartItemsList.innerHTML = "<p style='color:#94a3b8;'>Your cart is currently empty.</p>";
        checkoutBtn.disabled = true;
        return;
    }
    checkoutBtn.disabled = false;

    cart.forEach((item, idx) => {
        const row = document.createElement("div");
        row.className = "cart-item-row";
        row.innerHTML = `
            <span>${item.icon} ${item.title}</span>
            <strong>$${item.price.toFixed(2)}</strong>
        `;
        cartItemsList.appendChild(row);
    });
}

// Promo Code
applyPromoBtn.addEventListener("click", () => {
    const code = promoInput.value.trim().toUpperCase();
    if (code === "SAVE20") {
        appliedDiscount = 0.20;
        discountBadge.style.display = "block";
        updateCheckoutSummary();
    } else {
        alert("Invalid Coupon Code. Try 'SAVE20'");
    }
});

// Checkout Actions
cartIconBtn.addEventListener("click", () => {
    renderCartItems();
    updateCheckoutSummary();
    orderSuccessBanner.style.display = "none";
    checkoutModal.style.display = "flex";
});

closeCheckoutBtn.addEventListener("click", () => checkoutModal.style.display = "none");
cancelCheckoutBtn.addEventListener("click", () => checkoutModal.style.display = "none");

checkoutBtn.addEventListener("click", () => {
    if (cart.length === 0) return;
    const randomOrdId = "#ORD-" + Math.floor(10000 + Math.random() * 90000);
    confirmedOrderId.textContent = randomOrdId;
    orderSuccessBanner.style.display = "block";
    cart = [];
    appliedDiscount = 0.0;
    discountBadge.style.display = "none";
    updateCartUI();
});

// Authentication Handlers
navLoginBtn.addEventListener("click", () => {
    loginErrorAlert.style.display = "none";
    emailError.style.display = "none";
    passwordError.style.display = "none";
    loginModal.style.display = "flex";
});

closeLoginBtn.addEventListener("click", () => loginModal.style.display = "none");
cancelLoginBtn.addEventListener("click", () => loginModal.style.display = "none");

loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = loginEmail.value.trim();
    const pass = loginPassword.value;

    let hasError = false;
    if (!email) {
        emailError.style.display = "block";
        hasError = true;
    } else {
        emailError.style.display = "none";
    }

    if (!pass) {
        passwordError.style.display = "block";
        hasError = true;
    } else {
        passwordError.style.display = "none";
    }

    if (hasError) return;

    // Verify Demo Credentials
    if (email === "demo@qa-platform.io" && pass === "Password@123") {
        userSession = { email: email, name: "Demo Tester" };
        navLoginBtn.style.display = "none";
        userProfileBadge.style.display = "flex";
        loginModal.style.display = "none";
        loginForm.reset();
    } else {
        loginErrorAlert.style.display = "block";
    }
});

logoutBtn.addEventListener("click", () => {
    userSession = null;
    navLoginBtn.style.display = "block";
    userProfileBadge.style.display = "none";
});

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
    renderProducts(PRODUCTS);
});
