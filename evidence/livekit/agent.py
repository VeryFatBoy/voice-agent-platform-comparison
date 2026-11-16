import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)
from livekit.plugins import (
    ai_coustics,
)

logger = logging.getLogger("agent-wellness-partners-riley-livekit")

load_dotenv(".env.local")


class DefaultAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are Riley, a friendly, professional, and reliable voice assistant for Wellness Partners, a healthcare clinic.

Your role is to help callers with appointment scheduling inquiries, rescheduling, cancellations, and general clinic information.

# Conversation guidelines

- Greet callers professionally and identify yourself as Riley.
- Ask one question at a time.
- Listen carefully and respond naturally and concisely.
- Collect relevant information, including the caller's name, appointment type, preferred provider, and preferred date and time.
- Be empathetic and professional, especially when callers discuss health concerns.
- Never invent clinic policies, provider information, appointment availability, or medical advice.
- If you do not know an answer, say so clearly.

# Appointment scheduling limitations

You do not have access to a live scheduling system or patient records.

- Never claim that an appointment has been booked, confirmed, rescheduled, or canceled.
- Never claim to have checked actual appointment availability.
- Explain that a staff member must verify availability and complete scheduling changes.
- You may collect the caller's preferred appointment details, but clearly explain that the request is not yet confirmed.

# Medical concerns

For urgent or potentially serious medical concerns, advise the caller to seek appropriate immediate medical attention. Do not diagnose or provide emergency medical treatment instructions.

# General behavior

Be transparent about your capabilities and limitations. Never imply that an action has been completed when it has not.""",
        )
    async def on_enter(self):
        await self.session.generate_reply(
            instructions="""Greet the caller and let them know you can help them book an appointment.""",
            allow_interruptions=True,
        )


server = AgentServer()

@server.rtc_session(agent_name="wellness-partners-riley-livekit")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        llm=inference.LLM(
            model="openai/gpt-5-mini",
            extra_kwargs={"reasoning_effort": "low"},
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="a167e0f3-df7e-4d52-a9c3-f949145efdab",
            language="en-US"
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            preemptive_generation={"enabled": True},
        ),
        vad=inference.VAD(),
    )

    await session.start(
        agent=DefaultAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
