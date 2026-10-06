package com.example.studentmanagement.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "students")
public class Student {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    private String name;
    private String email;
    private String phone;
    private String course;
    private Integer age;
    protected Student() { }
    public Student(String name, String email, String phone, String course, Integer age) {
        this.name = name; this.email = email; this.phone = phone; this.course = course; this.age = age;
    }
    public Long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public String getPhone() { return phone; }
    public String getCourse() { return course; }
    public Integer getAge() { return age; }
    public void replace(String newName, String newEmail, String newPhone, String newCourse, Integer newAge) {
        name = newName; email = newEmail; phone = newPhone; course = newCourse; age = newAge;
    }
}
