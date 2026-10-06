package com.example.studentmanagement.kafka;

import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

@Component
public class StudentMutationEventListener {
    private final StudentEventProducer eventProducer;

    public StudentMutationEventListener(StudentEventProducer eventProducer) {
        this.eventProducer = eventProducer;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onStudentMutation(StudentEvent event) {
        eventProducer.publish(event);
    }
}
