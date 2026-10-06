package com.example.studentmanagement.repository;

import com.example.studentmanagement.entity.RefreshToken;
import com.example.studentmanagement.entity.Role;
import com.example.studentmanagement.entity.User;
import java.time.Instant;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.assertEquals;

@DataJpaTest
class RefreshTokenRepositoryTest {
    @Autowired private RefreshTokenRepository refreshTokenRepository;
    @Autowired private UserRepository userRepository;
    @Autowired private PlatformTransactionManager transactionManager;

    @Test
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    void concurrentConsumersAllowOnlyOneRefreshTokenConsumption() throws Exception {
        TransactionTemplate transactions = new TransactionTemplate(transactionManager);
        transactions.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        transactions.executeWithoutResult(status -> {
            User user = userRepository.save(new User("admin", "hash", Set.of(Role.ADMIN)));
            refreshTokenRepository.saveAndFlush(new RefreshToken("refresh-token", Instant.now().plusSeconds(60), user));
        });

        CountDownLatch start = new CountDownLatch(1);
        ExecutorService executor = Executors.newFixedThreadPool(2);
        try {
            Future<Boolean> first = executor.submit(() -> consume(transactions, start));
            Future<Boolean> second = executor.submit(() -> consume(transactions, start));
            start.countDown();

            assertEquals(1, (first.get() ? 1 : 0) + (second.get() ? 1 : 0));
        } finally {
            executor.shutdownNow();
        }
    }

    private boolean consume(TransactionTemplate transactions, CountDownLatch start) throws Exception {
        start.await();
        return transactions.execute(status -> {
            Optional<RefreshToken> token = refreshTokenRepository.findByTokenValueForUpdate("refresh-token");
            if (token.isEmpty() || token.get().isRevoked()) {
                return false;
            }
            token.get().revoke();
            return true;
        });
    }
}
