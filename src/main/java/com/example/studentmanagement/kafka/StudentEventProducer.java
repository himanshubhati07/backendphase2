package com.example.studentmanagement.kafka;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class StudentEventProducer {
    private static final Logger LOGGER = LoggerFactory.getLogger(StudentEventProducer.class);
    private static final String TOPIC = "student-events";
    private final KafkaTemplate<String, StudentEvent> kafkaTemplate;
    public StudentEventProducer(KafkaTemplate<String, StudentEvent> kafkaTemplate) { this.kafkaTemplate = kafkaTemplate; }
    public void publish(StudentEvent event) {
        kafkaTemplate.send(TOPIC, event.studentId().toString(), event).whenComplete((result, error) -> {
            if (error != null) { LOGGER.error("Kafka mutation event failed for studentId={}", event.studentId(), error); }
            else { LOGGER.info("Kafka mutation event published for studentId={}", event.studentId()); }
        });
    }
}
