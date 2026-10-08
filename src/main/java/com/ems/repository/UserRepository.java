package com.ems.repository;

import com.ems.entity.User;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Persistence access for {@link User} accounts, keyed by the unique login email.
 */
public interface UserRepository extends JpaRepository<User, Long> {

	Optional<User> findByEmail(String email);

	boolean existsByEmail(String email);
}
