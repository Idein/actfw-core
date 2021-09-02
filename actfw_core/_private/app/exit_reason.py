from typing import Optional, Protocol


class AppExitReason(Protocol):
    def application_event(self) -> Optional[AppEvent]:
        pass

class Hoge:
    def required_user_action(self) -> Optional[RequiredUserAction]:
        pass



@dataclass
class AppEvent:
    


class AppExitReasonUserActionRequired:
    action: UserAction


class UserAction:
    message: str
    document_flagment: Optional[str]



