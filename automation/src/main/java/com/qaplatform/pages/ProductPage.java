package com.qaplatform.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

/**
 * Page Object Model for ApexCart Product Catalog and Search.
 */
public class ProductPage extends BasePage {

    private final By searchInput = By.id("search-input");
    private final By searchBtn = By.id("search-btn");
    private final By productCards = By.className("product-card");
    private final By firstAddToCartBtn = By.cssSelector(".add-to-cart-btn:first-of-type");
    private final By cartBadge = By.id("cart-badge-count");
    private final By noResultsMessage = By.id("no-results-msg");

    public ProductPage(WebDriver driver) {
        super(driver);
    }

    public void searchProduct(String query) {
        type(searchInput, query);
        click(searchBtn);
    }

    public int getProductCount() {
        return driver.findElements(productCards).size();
    }

    public void addFirstItemToCart() {
        click(firstAddToCartBtn);
    }

    public String getCartCount() {
        return getText(cartBadge);
    }

    public boolean isNoResultsDisplayed() {
        return isElementDisplayed(noResultsMessage);
    }
}
