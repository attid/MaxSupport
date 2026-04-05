# Golden Principles of MaxSupport

1. **AI-First & Human-Verified**: Любой код, предложенный ИИ, должен соответствовать архитектуре. Если ИИ «галлюцинирует» обход слоев — это считается грубым нарушением.
2. **Domain Agnosticity**: Слой `domain` и `application` никогда не знают про `aiogram`, `telegram`, `mongodb`. Только абстрактные интерфейсы (Repository, BotInterface).
3. **Immutability of Logic**: Бизнес-логика живет в `domain`. Use-cases в `application` только оркестрируют домен.
4. **Single Responsibility**: Один хендлер = одна реакция. Один use case = одно действие.
5. **Fail-Fast**: Валидация входных данных (pydantic) на границах системы обязательна.
6. **No Global State**: Запрещено использование глобальных переменных `bot`, `db`, `config`. Всё инжектится через зависимости.
