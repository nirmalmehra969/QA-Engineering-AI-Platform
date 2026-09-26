package com.qaplatform.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

/**
 * Page Object Model for ApexCart Cart Drawer and Checkout Flow.
 */
public class CheckoutPage extends BasePage {

    private final By cartIconBtn = By.id("cart-icon-btn");
    private final By checkoutModal = By.id("checkout-modal");
    private final By promoInput = By.id("promo-input");
    private final By applyPromoBtn = By.id("apply-promo-btn");
    private final By discountBadge = By.id("discount-badge");
    private final By orderTotalPrice = By.id("order-total-price");
    private final By checkoutConfirmBtn = By.id("checkout-btn");
    private final By orderSuccessBanner = By.id("order-success-banner");
    private final By confirmedOrderId = By.id("confirmed-order-id");

    public CheckoutPage(WebDriver driver) {
        super(driver);
    }

    public void openCartDrawer() {
        click(cartIconBtn);
    }

    public void applyPromoCode(String code) {
        type(promoInput, code);
        click(applyPromoBtn);
    }

    public boolean isDiscountApplied() {
        return isElementDisplayed(discountBadge);
    }

    public String getTotalPrice() {
        return getText(orderTotalPrice);
    }

    public void completeCheckout() {
        click(checkoutConfirmBtn);
    }

    public boolean isOrderSuccessDisplayed() {
        return isElementDisplayed(orderSuccessBanner);
    }

    public String getConfirmedOrderId() {
        return getText(confirmedOrderId);
    }
}
