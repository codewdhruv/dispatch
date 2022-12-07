from dispatch.participant import service as participant_service


class RestrictedCommand:
    def __init__(self, allowed_roles: list = []):
        self.allowed_roles = allowed_roles

    async def __call__(self, body, next, context, respond, db_session, user, logger):
        if context["subject"].type == "case":
            logger.warning("Sensitive command middleware is not supported for cases.")
            next()

        participant = participant_service.get_by_incident_id_and_email(
            db_session=db_session, incident_id=context["subject"].id, email=user.email
        )

        # if any required role is active, allow command
        for active_role in participant.active_roles:
            for allowed_role in self.allowed_roles:
                if active_role.role == allowed_role:
                    next()

        await respond(
            text=f"I see you tried to run `{context['command']}`. This is a sensitive command and cannot be run with the incident role you are currently assigned.",
            response_type="ephemeral",
        )
