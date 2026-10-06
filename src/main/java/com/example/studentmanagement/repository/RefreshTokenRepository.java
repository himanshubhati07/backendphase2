package com.example.studentmanagement.repository;

import com.example.studentmanagement.entity.RefreshToken;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> { Optional<RefreshToken> findByTokenValue(String tokenValue); }
