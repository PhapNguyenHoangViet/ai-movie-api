def user_prompt_chat_node(user_input) -> str:
    return f"""
        {user_input}
    """


def user_prompt_chat_recommendation_node(movie_data, user_input) -> str:
    return f"""
        Dựa trên dữ liệu phim sau:
        movie_data: {movie_data}
        Các bộ phim này được sắp xếp theo thứ tự khuyến nghị ưu tiên, không được thay đổi thứ tự của các bộ phim.
        Hãy trả lời câu hỏi của người dùng sau:
        {user_input}
    """
