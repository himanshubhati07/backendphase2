package com.example.studentmanagement.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component @Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter extends OncePerRequestFilter {
    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        String id = request.getHeader("X-Request-ID");
        if (id == null || id.isBlank()) { id = request.getHeader("X-Correlation-ID"); }
        if (id == null || id.isBlank()) { id = UUID.randomUUID().toString(); }
        request.setAttribute("correlationId", id); response.setHeader("X-Request-ID", id); MDC.put("correlationId", id);
        try { chain.doFilter(request, response); } finally { MDC.remove("correlationId"); }
    }
}
