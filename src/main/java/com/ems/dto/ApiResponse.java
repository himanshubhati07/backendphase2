package com.ems.dto;

/**
 * Generic response envelope wrapping every controller response, success or error.
 *
 * @param <T> the type of the payload carried in {@link #data}
 */
public class ApiResponse<T> {

	private final boolean success;
	private final String message;
	private final T data;

	private ApiResponse(boolean success, String message, T data) {
		this.success = success;
		this.message = message;
		this.data = data;
	}

	public static <T> ApiResponse<T> success(T data) {
		return new ApiResponse<>(true, "Success", data);
	}

	public static <T> ApiResponse<T> success(String message, T data) {
		return new ApiResponse<>(true, message, data);
	}

	public static <T> ApiResponse<T> error(String message) {
		return new ApiResponse<>(false, message, null);
	}

	public boolean isSuccess() {
		return success;
	}

	public String getMessage() {
		return message;
	}

	public T getData() {
		return data;
	}
}
