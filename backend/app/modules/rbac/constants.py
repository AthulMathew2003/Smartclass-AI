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


class SubjectPermission:
    CREATE = "subject.create"
    READ = "subject.read"
    UPDATE = "subject.update"
    DELETE = "subject.delete"
    TEACHER_ADD = "subject.teacher.add"
    TEACHER_REMOVE = "subject.teacher.remove"


class AssignmentPermission:
    CREATE = "assignment.create"
    READ = "assignment.read"
    UPDATE = "assignment.update"
    DELETE = "assignment.delete"
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
