class SystemRole:
    OWNER = "Owner"
    ADMIN = "Admin"
    TEACHER = "Teacher"
    STUDENT = "Student"
    PARENT = "Parent"
    STAFF = "Staff"


class MemberPermission:
    CREATE = "member.create"
    READ = "member.read"
    UPDATE = "member.update"
    DELETE = "member.delete"


class WorkspacePermission:
    CREATE = "workspace.create"
    READ = "workspace.read"
    UPDATE = "workspace.update"
    DELETE = "workspace.delete"


class OrganizationPermission:
    UPDATE = "organization.update"


class ClassroomPermission:
    CREATE = "classroom.create"
    UPDATE = "classroom.update"


class AssignmentPermission:
    CREATE = "assignment.create"
    UPDATE = "assignment.update"
    GRADE = "assignment.grade"


class AttendancePermission:
    VIEW = "attendance.view"
    MANAGE = "attendance.manage"


class ExamPermission:
    CREATE = "exam.create"
    PUBLISH = "exam.publish"


class AnalyticsPermission:
    VIEW = "analytics.view"


class AIPermission:
    USE = "ai.use"


class SettingsPermission:
    MANAGE = "settings.manage"
