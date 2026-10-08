package com.ems.repository;

import com.ems.entity.Employee;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/**
 * Spring Data repository for {@link Employee}.
 */
public interface EmployeeRepository extends JpaRepository<Employee, Long> {

	boolean existsByEmail(String email);

	boolean existsByEmailAndIdNot(String email, Long id);

	/**
	 * Filters by name (matched against first OR last name), email, and department,
	 * case-insensitively. Any parameter left {@code null} is not filtered on at all.
	 */
	@Query("""
			select e from Employee e where
			(:name is null or lower(e.firstName) like lower(concat('%', :name, '%'))
				or lower(e.lastName) like lower(concat('%', :name, '%')))
			and (:email is null or lower(e.email) like lower(concat('%', :email, '%')))
			and (:department is null or lower(e.department) like lower(concat('%', :department, '%')))
			""")
	Page<Employee> search(
			@Param("name") String name,
			@Param("email") String email,
			@Param("department") String department,
			Pageable pageable);
}
