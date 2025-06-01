def system_prompt_chat_node() -> str:
    return """
        Bạn là một trợ lý ảo thông minh. Dựa vào câu hỏi của người dùng giúp tôi phân tích
        người dùng đang muốn sử dụng khuyến nghị phim thì trả về "chat_recommendation_node"
        còn không thì trả về "chat_knowledgebase_node".
    """


def system_prompt_chat_recommendation_node() -> str:
    return """
        trả lời câu hỏi của User trên bằng ngôn ngữ người dùng đưa vào (mặc định là tiếng Việt).
        giữ thứ tự recommendation là quan trọng, không được thay đổi thứ tự của các recommendation.
        Output dạng text, không có định dạng markdown hay html.
    """
