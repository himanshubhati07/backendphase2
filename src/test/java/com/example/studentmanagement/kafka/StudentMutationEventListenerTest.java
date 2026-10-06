package com.example.studentmanagement.kafka;

import com.example.studentmanagement.dto.StudentResponse;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.transaction.support.AbstractPlatformTransactionManager;
import org.springframework.transaction.support.DefaultTransactionStatus;
import org.springframework.transaction.support.TransactionTemplate;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

class StudentMutationEventListenerTest {
    @Test
    void publishesOnlyAfterTheTransactionCommits() {
        StudentEventProducer producer = mock(StudentEventProducer.class);
        StudentEvent event = event();
        try (AnnotationConfigApplicationContext context = listenerContext(producer)) {
            TransactionTemplate transactionTemplate = new TransactionTemplate(new TestTransactionManager());

            transactionTemplate.executeWithoutResult(status -> {
                context.publishEvent(event);
                verifyNoInteractions(producer);
            });

            verify(producer).publish(event);
        }
    }

    @Test
    void delegatesTheCommittedEventToTheProducer() {
        StudentEventProducer producer = mock(StudentEventProducer.class);
        StudentEvent event = event();
        StudentMutationEventListener listener = new StudentMutationEventListener(producer);

        listener.onStudentMutation(event);

        verify(producer).publish(event);
    }

    private AnnotationConfigApplicationContext listenerContext(StudentEventProducer producer) {
        AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext();
        context.registerBean(StudentEventProducer.class, () -> producer);
        context.register(TransactionalEventConfiguration.class, StudentMutationEventListener.class);
        context.refresh();
        return context;
    }

    private StudentEvent event() {
        StudentResponse student = new StudentResponse(1L, "Ada", "ada@example.com", "123", "Math", 20);
        return new StudentEvent(StudentEventType.CREATE, 1L, Instant.parse("2025-01-01T00:00:00Z"), student);
    }

    @Configuration
    @EnableTransactionManagement
    static class TransactionalEventConfiguration {
        // Enables the transactional event listener factory for this focused context.
    }

    private static final class TestTransactionManager extends AbstractPlatformTransactionManager {
        @Override
        protected Object doGetTransaction() {
            return new Object();
        }

        @Override
        protected void doBegin(Object transaction, TransactionDefinition definition) {
            // No resource is needed by this in-memory transaction manager.
        }

        @Override
        protected void doCommit(DefaultTransactionStatus status) {
            // Transaction synchronization invokes the AFTER_COMMIT listener.
        }

        @Override
        protected void doRollback(DefaultTransactionStatus status) {
            // No resource is needed by this in-memory transaction manager.
        }
    }
}
