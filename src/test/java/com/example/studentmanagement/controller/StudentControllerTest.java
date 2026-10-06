package com.example.studentmanagement.controller;

import com.example.studentmanagement.dto.StudentPageResponse;
import com.example.studentmanagement.dto.StudentResponse;
import com.example.studentmanagement.service.StudentService;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class StudentControllerTest {
    private StudentService service;
    private MockMvc mvc;
    @BeforeEach void setup() { service = mock(StudentService.class); mvc = MockMvcBuilders.standaloneSetup(new StudentController(service)).build(); }
    @Test void createReturns201() throws Exception { when(service.create(any())).thenReturn(student()); mvc.perform(post("/api/v1/students").contentType(MediaType.APPLICATION_JSON).content(body())).andExpect(status().isCreated()); }
    @Test void listUsesDefaults() throws Exception { when(service.list(0, 20)).thenReturn(new StudentPageResponse(List.of(), 0, 20, 0)); mvc.perform(get("/api/v1/students")).andExpect(status().isOk()); verify(service).list(0, 20); }
    @Test void getAndUpdateRoute() throws Exception { when(service.get(1L)).thenReturn(student()); when(service.update(eq(1L), any())).thenReturn(student()); mvc.perform(get("/api/v1/students/1")).andExpect(status().isOk()); mvc.perform(put("/api/v1/students/1").contentType(MediaType.APPLICATION_JSON).content(body())).andExpect(status().isOk()); }
    @Test void invalidRequestIs400() throws Exception { mvc.perform(post("/api/v1/students").contentType(MediaType.APPLICATION_JSON).content("{}")) .andExpect(status().isBadRequest()); }
    @Test void deleteReturns204() throws Exception { mvc.perform(delete("/api/v1/students/1")).andExpect(status().isNoContent()); verify(service).delete(1L); }
    private StudentResponse student() { return new StudentResponse(1L, "Ada", "ada@example.com", "123", "Math", 20); }
    private String body() { return "{\"name\":\"Ada\",\"email\":\"ada@example.com\",\"phone\":\"123\",\"course\":\"Math\",\"age\":20}"; }
}
