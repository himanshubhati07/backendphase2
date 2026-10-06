package com.example.studentmanagement.repository;

import com.example.studentmanagement.entity.User;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
public interface UserRepository extends JpaRepository<User, Long> { Optional<User> findByUsername(String username); }
