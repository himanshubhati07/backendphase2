package com.example.studentmanagement.security;

import org.springframework.boot.context.properties.ConfigurationProperties;
@ConfigurationProperties(prefix = "app.jwt")
public class JwtProperties {
    private String secret;
    private long accessTokenExpirationMinutes = 480;
    private long refreshTokenExpirationMinutes = 10080;
    public String getSecret() { return secret; }
    public void setSecret(String secret) { this.secret = secret; }
    public long getAccessTokenExpirationMinutes() { return accessTokenExpirationMinutes; }
    public void setAccessTokenExpirationMinutes(long value) { accessTokenExpirationMinutes = value; }
    public long getRefreshTokenExpirationMinutes() { return refreshTokenExpirationMinutes; }
    public void setRefreshTokenExpirationMinutes(long value) { refreshTokenExpirationMinutes = value; }
}
