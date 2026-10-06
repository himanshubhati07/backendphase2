package com.example.studentmanagement.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToOne;
import java.time.Instant;

@Entity
public class RefreshToken {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    private String tokenValue;
    private Instant expiry;
    private boolean revoked;
    @ManyToOne(fetch = FetchType.LAZY, optional = false) private User owner;
    protected RefreshToken() { }
    public RefreshToken(String tokenValue, Instant expiry, User owner) { this.tokenValue = tokenValue; this.expiry = expiry; this.owner = owner; }
    public Long getId() { return id; }
    public String getTokenValue() { return tokenValue; }
    public Instant getExpiry() { return expiry; }
    public boolean isRevoked() { return revoked; }
    public User getOwner() { return owner; }
    public void revoke() { revoked = true; }
}
