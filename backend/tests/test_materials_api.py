import uuid
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient
from app.modules.users.service import UserService


async def _create_user_and_login(client: AsyncClient, user_service: UserService, email: str, name: str) -> dict:
    user = await user_service.create_user(
        email=email,
        password="Password123!",
        first_name=name,
        last_name="User"
    )
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


@pytest.fixture(autouse=True)
def mock_s3_storage():
    with patch("app.modules.subjects.material_service.S3StorageService") as mock_cls:
        instance = MagicMock()
        instance.generate_upload_url.return_value = "https://s3.ap-south-1.amazonaws.com/presigned-put-material"
        instance.generate_download_url.return_value = "https://s3.ap-south-1.amazonaws.com/presigned-get-material"
        instance.object_exists.return_value = True
        instance.delete_object.return_value = None
        mock_cls.return_value = instance
        yield instance


@pytest.mark.asyncio
async def test_material_full_lifecycle_and_rbac(client: AsyncClient, db_session, mock_s3_storage):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "mat_owner@test.com", "Owner")
    teacher1_data = await _create_user_and_login(client, user_service, "mat_assigned@test.com", "Teacher1")
    teacher2_data = await _create_user_and_login(client, user_service, "mat_unassigned@test.com", "Teacher2")
    student_data = await _create_user_and_login(client, user_service, "mat_student@test.com", "Student")
    await db_session.commit()

    # 1. Onboard Organization
    onboard_res = await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Material Org", "org_slug": "material-org", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "Grade 10"
    }, headers=owner_data["headers"])
    assert onboard_res.status_code == 200

    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher1_data["headers"]["X-Organization-Id"] = org_id
    teacher2_data["headers"]["X-Organization-Id"] = org_id
    student_data["headers"]["X-Organization-Id"] = org_id

    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    roles = roles_res.json()
    teacher_role_id = next(r["role_id"] for r in roles if r["role_name"] == "Teacher")
    student_role_id = next(r["role_id"] for r in roles if r["role_name"] == "Student")

    # Add members to Workspace
    await client.post("/api/v1/organizations/members", json={
        "email": "mat_assigned@test.com", "first_name": "T1", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "mat_unassigned@test.com", "first_name": "T2", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "mat_student@test.com", "first_name": "S", "last_name": "U", "role_id": student_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject & assign Teacher 1
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Computer Science"
    }, headers=owner_data["headers"])
    assert sub_res.status_code == 201
    subject_id = sub_res.json()["subject_id"]

    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher1_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # ── 2. RBAC Upload Intent ──
    # Student blocked -> 403
    student_req = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/upload-url",
        json={
            "title": "Lecture 1",
            "category": "Lecture",
            "original_filename": "lecture1.pdf",
            "content_type": "application/pdf",
            "file_size": 2048
        },
        headers=student_data["headers"]
    )
    assert student_req.status_code == 403

    # Unassigned Teacher blocked -> 403
    unassigned_req = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/upload-url",
        json={
            "title": "Lecture 1",
            "category": "Lecture",
            "original_filename": "lecture1.pdf",
            "content_type": "application/pdf",
            "file_size": 2048
        },
        headers=teacher2_data["headers"]
    )
    assert unassigned_req.status_code == 403

    # Assigned Teacher 1 requests upload URL -> 201
    upload_res = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/upload-url",
        json={
            "title": "Introduction to Algorithms",
            "description": "Chapter 1 Lecture Slides",
            "category": "Lecture",
            "original_filename": "intro_algorithms.pdf",
            "content_type": "application/pdf",
            "file_size": 1024 * 500  # 500 KB
        },
        headers=teacher1_data["headers"]
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    assert "upload_url" in upload_data
    assert "s3_key" in upload_data
    assert upload_data["s3_key"].startswith(f"subjects/{subject_id}/materials/")
    material_id = upload_data["material_id"]

    # ── 3. S3 Confirmation ──
    # Confirm with mismatched S3 key -> 400/422
    bad_confirm = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}/confirm",
        json={"s3_key": "some/fake/key.pdf"},
        headers=teacher1_data["headers"]
    )
    assert bad_confirm.status_code in (400, 422)

    # Confirm when S3 object does not exist -> 400
    mock_s3_storage.object_exists.return_value = False
    fail_confirm = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}/confirm",
        json={"s3_key": upload_data["s3_key"]},
        headers=teacher1_data["headers"]
    )
    assert fail_confirm.status_code in (400, 422)

    # Successful confirmation
    mock_s3_storage.object_exists.return_value = True
    confirm_res = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}/confirm",
        json={"s3_key": upload_data["s3_key"]},
        headers=teacher1_data["headers"]
    )
    assert confirm_res.status_code == 200
    mat_data = confirm_res.json()
    assert mat_data["material_id"] == material_id
    assert mat_data["title"] == "Introduction to Algorithms"
    assert mat_data["category"] == "Lecture"
    assert mat_data["status"] == "active"
    assert mat_data["uploaded_by"]["user_id"] == str(teacher1_data["user"].user_id)

    # ── 4. Reading & Listing Materials ──
    # Student lists materials -> sees the confirmed material
    student_list = await client.get(
        f"/api/v1/subjects/{subject_id}/materials",
        headers=student_data["headers"]
    )
    assert student_list.status_code == 200
    assert len(student_list.json()) == 1
    assert student_list.json()[0]["material_id"] == material_id

    # Unassigned Teacher reads list -> 200
    t2_list = await client.get(
        f"/api/v1/subjects/{subject_id}/materials",
        headers=teacher2_data["headers"]
    )
    assert t2_list.status_code == 200
    assert len(t2_list.json()) == 1

    # Single material get
    get_res = await client.get(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        headers=student_data["headers"]
    )
    assert get_res.status_code == 200
    assert get_res.json()["material_id"] == material_id

    # Download URL generation for student
    download_res = await client.get(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}/download-url",
        headers=student_data["headers"]
    )
    assert download_res.status_code == 200
    assert "download_url" in download_res.json()

    # ── 5. Metadata Update ──
    # Student cannot update -> 403
    assert (await client.patch(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        json={"title": "Hacked Title"},
        headers=student_data["headers"]
    )).status_code == 403

    # Unassigned teacher cannot update -> 403
    assert (await client.patch(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        json={"title": "Teacher 2 Edit"},
        headers=teacher2_data["headers"]
    )).status_code == 403

    # Assigned teacher updates title and category -> 200
    update_res = await client.patch(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        json={"title": "Intro to Algorithms V2", "category": "Study Material"},
        headers=teacher1_data["headers"]
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Intro to Algorithms V2"
    assert update_res.json()["category"] == "Study Material"

    # ── 6. Category Filtering & Search ──
    # Search match
    search_hit = await client.get(
        f"/api/v1/subjects/{subject_id}/materials?search=Algorithms",
        headers=student_data["headers"]
    )
    assert len(search_hit.json()) == 1

    # Search miss
    search_miss = await client.get(
        f"/api/v1/subjects/{subject_id}/materials?search=NonExistentSubjectXYZ",
        headers=student_data["headers"]
    )
    assert len(search_miss.json()) == 0

    # Category match
    cat_hit = await client.get(
        f"/api/v1/subjects/{subject_id}/materials?category=Study Material",
        headers=student_data["headers"]
    )
    assert len(cat_hit.json()) == 1

    # Category miss
    cat_miss = await client.get(
        f"/api/v1/subjects/{subject_id}/materials?category=Lab",
        headers=student_data["headers"]
    )
    assert len(cat_miss.json()) == 0

    # ── 7. Soft Archive / Delete ──
    # Student cannot delete -> 403
    assert (await client.delete(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        headers=student_data["headers"]
    )).status_code == 403

    # Unassigned teacher cannot delete -> 403
    assert (await client.delete(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        headers=teacher2_data["headers"]
    )).status_code == 403

    # Assigned teacher archives material -> 200
    archive_res = await client.delete(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        headers=teacher1_data["headers"]
    )
    assert archive_res.status_code == 200

    # Student listing active materials -> now returns 0
    s_list_after = await client.get(
        f"/api/v1/subjects/{subject_id}/materials",
        headers=student_data["headers"]
    )
    assert len(s_list_after.json()) == 0

    # Student direct get on archived material -> 404
    assert (await client.get(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}",
        headers=student_data["headers"]
    )).status_code == 404

    # Student download on archived material -> 404
    assert (await client.get(
        f"/api/v1/subjects/{subject_id}/materials/{material_id}/download-url",
        headers=student_data["headers"]
    )).status_code == 404

    # Teacher viewing archived filter -> 1
    t_arch_list = await client.get(
        f"/api/v1/subjects/{subject_id}/materials?status=archived",
        headers=teacher1_data["headers"]
    )
    assert len(t_arch_list.json()) == 1
    assert t_arch_list.json()[0]["material_id"] == material_id


@pytest.mark.asyncio
async def test_material_validation_and_unsupported_types(client: AsyncClient, db_session, mock_s3_storage):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "val_owner@test.com", "Owner")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Validation Org", "org_slug": "val-org", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "Main WS"
    }, headers=owner_data["headers"])

    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id

    ws_id = (await client.get("/api/v1/workspaces", headers=owner_data["headers"])).json()[0]["workspace_id"]
    sub_res = await client.post("/api/v1/subjects", json={"workspace_id": ws_id, "subject_name": "Physics"}, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]

    # 1. Valid Supported Types
    valid_types = [
        ("doc.pdf", "application/pdf", 1024),
        ("notes.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 2048),
        ("slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", 4096),
        ("sheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 1024),
        ("data.csv", "text/csv", 512),
        ("plain.txt", "text/plain", 128),
        ("photo.png", "image/png", 1024 * 1024),
        ("diagram.jpg", "image/jpeg", 1024 * 500),
        ("graphic.webp", "image/webp", 1024 * 300),
        ("clip.mp4", "video/mp4", 1024 * 1024 * 10),
        ("archive.zip", "application/zip", 1024 * 1024 * 5),
    ]

    for filename, content_type, file_size in valid_types:
        res = await client.post(
            f"/api/v1/subjects/{subject_id}/materials/upload-url",
            json={
                "title": f"Valid {filename}",
                "category": "Notes",
                "original_filename": filename,
                "content_type": content_type,
                "file_size": file_size
            },
            headers=owner_data["headers"]
        )
        assert res.status_code == 201, f"Failed for {filename}: {res.text}"

    # 2. Unsupported / Dangerous Formats Rejected
    bad_types = [
        ("image.svg", "image/svg+xml", 1024),  # SVG rejected
        ("script.js", "application/javascript", 1024),
        ("page.html", "text/html", 1024),
        ("program.exe", "application/x-msdownload", 1024),
        ("script.sh", "application/x-sh", 1024),
        ("mismatched.pdf", "image/png", 1024),  # MIME and extension mismatch
    ]

    for filename, content_type, file_size in bad_types:
        res = await client.post(
            f"/api/v1/subjects/{subject_id}/materials/upload-url",
            json={
                "title": f"Bad {filename}",
                "category": "Notes",
                "original_filename": filename,
                "content_type": content_type,
                "file_size": file_size
            },
            headers=owner_data["headers"]
        )
        assert res.status_code in (400, 422), f"Expected error for {filename}, got {res.status_code}"

    # 3. Oversized Files Rejected
    # Image > 10MB
    res_img_big = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/upload-url",
        json={
            "title": "Huge Image",
            "category": "Notes",
            "original_filename": "huge.png",
            "content_type": "image/png",
            "file_size": 1024 * 1024 * 15  # 15 MB
        },
        headers=owner_data["headers"]
    )
    assert res_img_big.status_code in (400, 422)

    # Document > 50MB
    res_doc_big = await client.post(
        f"/api/v1/subjects/{subject_id}/materials/upload-url",
        json={
            "title": "Huge Doc",
            "category": "Notes",
            "original_filename": "huge.pdf",
            "content_type": "application/pdf",
            "file_size": 1024 * 1024 * 60  # 60 MB
        },
        headers=owner_data["headers"]
    )
    assert res_doc_big.status_code in (400, 422)


@pytest.mark.asyncio
async def test_material_multi_tenant_isolation(client: AsyncClient, db_session, mock_s3_storage):
    user_service = UserService(db_session)
    owner1_data = await _create_user_and_login(client, user_service, "tenant1_owner@test.com", "Owner1")
    owner2_data = await _create_user_and_login(client, user_service, "tenant2_owner@test.com", "Owner2")
    await db_session.commit()

    # 1. Setup Org 1
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org One", "org_slug": "org-one", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "O1", "owner_last_name": "U", "owner_phone": "1", "workspace_name": "WS1"
    }, headers=owner1_data["headers"])
    org1_id = (await client.get("/api/v1/organizations/memberships", headers=owner1_data["headers"])).json()[0]["organization_id"]
    owner1_data["headers"]["X-Organization-Id"] = org1_id
    ws1_id = (await client.get("/api/v1/workspaces", headers=owner1_data["headers"])).json()[0]["workspace_id"]
    sub1_id = (await client.post("/api/v1/subjects", json={"workspace_id": ws1_id, "subject_name": "Math 1"}, headers=owner1_data["headers"])).json()["subject_id"]

    # 2. Setup Org 2
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org Two", "org_slug": "org-two", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "O2", "owner_last_name": "U", "owner_phone": "2", "workspace_name": "WS2"
    }, headers=owner2_data["headers"])
    org2_id = (await client.get("/api/v1/organizations/memberships", headers=owner2_data["headers"])).json()[0]["organization_id"]
    owner2_data["headers"]["X-Organization-Id"] = org2_id
    ws2_id = (await client.get("/api/v1/workspaces", headers=owner2_data["headers"])).json()[0]["workspace_id"]
    sub2_id = (await client.post("/api/v1/subjects", json={"workspace_id": ws2_id, "subject_name": "Math 2"}, headers=owner2_data["headers"])).json()["subject_id"]

    # 3. Create material in Org 1
    mat1_req = await client.post(
        f"/api/v1/subjects/{sub1_id}/materials/upload-url",
        json={"title": "Org 1 Secret Material", "category": "Notes", "original_filename": "secret.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=owner1_data["headers"]
    )
    mat1_id = mat1_req.json()["material_id"]

    # 4. Cross-Tenant Attacks by Org 2 Owner
    # List materials of Org 1 subject using Org 2 headers -> 404 (or 403)
    assert (await client.get(f"/api/v1/subjects/{sub1_id}/materials", headers=owner2_data["headers"])).status_code in (403, 404)

    # Get material of Org 1 using Org 2 headers and Org 1 subject ID -> 404/403
    assert (await client.get(f"/api/v1/subjects/{sub1_id}/materials/{mat1_id}", headers=owner2_data["headers"])).status_code in (403, 404)

    # Get material of Org 1 using Org 2 headers and Org 2 subject ID (forged subject ID) -> 404
    assert (await client.get(f"/api/v1/subjects/{sub2_id}/materials/{mat1_id}", headers=owner2_data["headers"])).status_code == 404

    # Download material of Org 1 using Org 2 headers -> 404/403
    assert (await client.get(f"/api/v1/subjects/{sub1_id}/materials/{mat1_id}/download-url", headers=owner2_data["headers"])).status_code in (403, 404)

    # Update material of Org 1 using Org 2 headers -> 404/403
    assert (await client.patch(f"/api/v1/subjects/{sub1_id}/materials/{mat1_id}", json={"title": "Hacked"}, headers=owner2_data["headers"])).status_code in (403, 404)

    # Delete material of Org 1 using Org 2 headers -> 404/403
    assert (await client.delete(f"/api/v1/subjects/{sub1_id}/materials/{mat1_id}", headers=owner2_data["headers"])).status_code in (403, 404)
