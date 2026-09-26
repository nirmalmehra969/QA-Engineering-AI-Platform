package com.qaplatform.tests;

import com.qaplatform.pages.CheckoutPage;
import com.qaplatform.pages.ProductPage;
import org.testng.Assert;
import org.testng.annotations.Test;

/**
 * End-to-End Shopping Cart & Checkout test suite.
 */
public class CheckoutTest extends BaseTest {

    @Test(priority = 1, description = "Verify adding product to cart increments badge counter")
    public void testAddToCart() {
        ProductPage productPage = new ProductPage(driver);
        productPage.addFirstItemToCart();
        Assert.assertEquals(productPage.getCartCount(), "1", "Cart counter badge should increment to 1");
    }

    @Test(priority = 2, description = "Verify coupon code 'SAVE20' calculation and order confirmation")
    public void testPromoCheckout() {
        ProductPage productPage = new ProductPage(driver);
        productPage.addFirstItemToCart();

        CheckoutPage checkoutPage = new CheckoutPage(driver);
        checkoutPage.openCartDrawer();
        checkoutPage.applyPromoCode("SAVE20");
        Assert.assertTrue(checkoutPage.isDiscountApplied(), "20% discount badge should be displayed");

        checkoutPage.completeCheckout();
        Assert.assertTrue(checkoutPage.isOrderSuccessDisplayed(), "Order success confirmation banner should appear");
        Assert.assertTrue(checkoutPage.getConfirmedOrderId().startsWith("#ORD-"), "Valid Order ID should be generated");
    }
}
