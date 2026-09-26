package com.qaplatform.tests;

import com.qaplatform.pages.LoginPage;
import org.testng.Assert;
import org.testng.annotations.Test;

/**
 * Authentication and Login acceptance test suite.
 */
public class LoginTest extends BaseTest {

    @Test(priority = 1, description = "Verify successful authentication with valid credentials")
    public void testValidLogin() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.login("demo@qa-platform.io", "Password@123");
        Assert.assertTrue(loginPage.isUserLoggedIn(), "User welcome profile badge should be visible on dashboard");
    }

    @Test(priority = 2, description = "Verify error messaging on invalid password attempt")
    public void testInvalidPassword() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.login("demo@qa-platform.io", "WrongPassword999");
        Assert.assertTrue(loginPage.getErrorMessage().contains("Invalid"), "Error alert should be displayed for invalid credentials");
    }

    @Test(priority = 3, description = "Verify validation triggers on empty required login fields")
    public void testEmptyFieldsValidation() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.login("", "");
        Assert.assertTrue(loginPage.isEmailValidationErrorShown(), "Email validation error should be visible");
        Assert.assertTrue(loginPage.isPasswordValidationErrorShown(), "Password validation error should be visible");
    }
}
