package com.qaplatform.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

/**
 * Page Object Model for ApexCart Authentication & Login Dialog.
 */
public class LoginPage extends BasePage {

    // Web Element Locators
    private final By navLoginBtn = By.id("nav-login-btn");
    private final By emailInput = By.id("login-email");
    private final By passwordInput = By.id("login-password");
    private final By submitBtn = By.id("login-submit-btn");
    private final By errorAlert = By.id("login-error-alert");
    private final By userProfileBadge = By.id("user-profile-badge");
    private final By emailValidation = By.id("email-error");
    private final By passwordValidation = By.id("password-error");

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void openLoginModal() {
        click(navLoginBtn);
    }

    public void login(String email, String password) {
        openLoginModal();
        type(emailInput, email);
        type(passwordInput, password);
        click(submitBtn);
    }

    public boolean isUserLoggedIn() {
        return isElementDisplayed(userProfileBadge);
    }

    public String getErrorMessage() {
        return getText(errorAlert);
    }

    public boolean isEmailValidationErrorShown() {
        return isElementDisplayed(emailValidation);
    }

    public boolean isPasswordValidationErrorShown() {
        return isElementDisplayed(passwordValidation);
    }
}
