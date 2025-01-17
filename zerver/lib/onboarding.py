from typing import Dict, List

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from zerver.actions.create_realm import setup_realm_internal_bots
from zerver.actions.message_send import (
    do_send_messages,
    internal_prep_stream_message_by_name,
    internal_send_private_message,
)
from zerver.actions.reactions import do_add_reaction
from zerver.lib.emoji import emoji_name_to_emoji_code
from zerver.lib.message import SendMessageRequest
from zerver.models import Message, Realm, UserProfile, get_system_bot


def missing_any_realm_internal_bots() -> bool:
    bot_emails = [
        bot["email_template"] % (settings.INTERNAL_BOT_DOMAIN,)
        for bot in settings.REALM_INTERNAL_BOTS
    ]
    realm_count = Realm.objects.count()
    return UserProfile.objects.filter(email__in=bot_emails).values("email").annotate(
        count=Count("id")
    ).filter(count=realm_count).count() != len(bot_emails)


def create_if_missing_realm_internal_bots() -> None:
    """This checks if there is any realm internal bot missing.

    If that is the case, it creates the missing realm internal bots.
    """
    if missing_any_realm_internal_bots():
        for realm in Realm.objects.all():
            setup_realm_internal_bots(realm)


def send_initial_direct_message(user: UserProfile) -> None:
    # We adjust the initial Welcome Bot direct message for education organizations.
    education_organization = False
    if (
        user.realm.org_type == Realm.ORG_TYPES["education_nonprofit"]["id"]
        or user.realm.org_type == Realm.ORG_TYPES["education"]["id"]
    ):
        education_organization = True

    # We need to override the language in this code path, because it's
    # called from account registration, which is a pre-account API
    # request and thus may not have the user's language context yet.
    with override_language(user.default_language):
        if education_organization:
            getting_started_help = user.realm.uri + "/help/using-zulip-for-a-class"
            getting_started_string = (
                _(
                    "If you are new to Practice Chat, check out our [Using Zulip for a class guide]({getting_started_url})!"
                )
            ).format(getting_started_url=getting_started_help)
        else:
            getting_started_help = user.realm.uri + "/help/getting-started-with-zulip"
            getting_started_string = (
                _(
                    "If you are new to Practice Chat, check out our [Getting started guide]({getting_started_url})!"
                )
            ).format(getting_started_url=getting_started_help)

        content = "".join(
            [
                "🤖" + _("Welcome to Practice Chat!") + "🤖" + "\n",
                _("I'm your friendly Welcome Bot, here to assist you as you embark on your journey with us. We're thrilled to have you as a new user and look forward to supporting you every step of the way.") + "\n\n",
                _("At Practice Chat, we offer a range of powerful features designed to streamline your practice and enhance communication. Allow me to introduce you to two helpful bots that will make your experience even more efficient:") + "\n",
                _("Meet our Office Bot: It specializes in answering questions related to office procedures and protocols. For example, you can ask, \"What is our procedure for dealing with a difficult patient?\" or \"How do we handle insurance claims?\" The Office Bot is here to provide you with valuable insights and guidance.") + "\n",
                _("Introducing our Clinical Bot: It's trained to answer specific clinical questions and provide expert knowledge. For instance, you can ask, \"Do I need to pre-medicate a patient who had a joint replaced?\" or \"What's the normal HbA1c range for a diabetic patient?\" The Clinical Bot is equipped with vast information from dental textbooks, ADA journals, and more.") + "\n",
                _("If you have any queries, need guidance, or simply want to say hello, just type your message, and I'll be here to assist you. Welcome once again, and let's make your experience with Practice Chat exceptional!") + "🌟" + "\n",
            ]
        )

    internal_send_private_message(
        get_system_bot(settings.WELCOME_BOT, user.realm_id),
        user,
        content,
        # Note: Welcome bot doesn't trigger email/push notifications,
        # as this is intended to be seen contextually in the application.
        disable_external_notifications=True,
    )

    clinical_bot_content = "".join(
        [
            "🤖" + _("Clinical Bot Welcomes You!") + "🤖" + "\n",
            _("Greetings! I'm your Clinical Bot, equipped with a wealth of knowledge sourced from a vast array of dental textbooks, ADA journals, and various reputable resources. I'm here to assist you with any questions you may have regarding dental procedures, protocols, and patient care. It's a pleasure to meet you!") + "\n\n",
            _("If you're seeking guidance on specific dental scenarios or need information about best practices in dentistry, feel free to ask. With my extensive training, I can provide you with accurate and reliable information. Here are a few examples of questions you can ask me:") + "\n",
            _("\"Do I need to pre-medicate a patient who had a joint replaced?\"") + "\n",
            _("\"What's the recommended fluoride concentration for pediatric patients?\"") + "\n",
            _("\"What are the steps for performing a root canal treatment?\"") + "\n",
            _("Please remember that while I strive to offer comprehensive and up-to-date information, I am an AI language model and not a substitute for professional dental advice. For complex cases or personalized treatment plans, it's always advisable to consult a qualified dentist or dental professional.") + "\n\n",
            _("Rest assured that I'm here to support you in understanding dental procedures, interpreting guidelines, and exploring the latest research. Together, we can ensure the delivery of exceptional dental care to our patients.") + "\n\n",
            _("Welcome to Practice Chat! If you have any questions or need assistance, don't hesitate to ask. Just type in your queries, and I'll provide you with the information you need. Let's work together to promote dental health and provide the highest standard of care!") + "🦷🌟" + "\n",
        ]
    )

    internal_send_private_message(
        get_system_bot(settings.CLINICAL_BOT + user.realm.host, user.realm_id),
        user,
        clinical_bot_content,
        # Note: Welcome bot doesn't trigger email/push notifications,
        # as this is intended to be seen contextually in the application.
        disable_external_notifications=True,
    )

    office_bot_content = "".join(
        [
            "🤖" + _("Office Bot Welcomes You!") + "🤖" + "\n",
            _("Hey there! I'm your Office Bot, here to assist you with all your questions regarding office procedures and protocols. It's a pleasure to meet you! Whether you're new to the office or just need a refresher, I'm here to provide you with the information you need.") + "\n\n",
            _("If you have any inquiries about our protocols or need guidance on specific office procedures, feel free to ask. I'm well-versed in a wide range of topics and can help you navigate through various situations. For instance, you can ask me questions like:") + "\n",
            _("\"What is our procedure for dealing with a difficult patient?\"") + "\n",
            _("\"How should I handle a scheduling conflict?\"") + "\n",
            _("\"What are the protocols for maintaining patient privacy and confidentiality?\"") + "\n",
            _("No matter what your question is, I'll do my best to provide you with accurate and up-to-date information. If there's something I can't assist with, I'll let you know and direct you to the appropriate resources or personnel.") + "\n\n",
            _("Remember, I'm here to support you and ensure a smooth experience in our office. Just type your questions, and I'll be ready to lend a virtual hand. Let's get started and make your time here as efficient and productive as possible!") + "\n\n",
            _("Once again, welcome to Practice Chat, and don't hesitate to reach out whenever you need assistance.") + "🦷🌟" + "\n",
        ]
    )

    internal_send_private_message(
        get_system_bot(settings.OFFICE_BOT + user.realm.host, user.realm_id),
        user,
        office_bot_content,
        # Note: Welcome bot doesn't trigger email/push notifications,
        # as this is intended to be seen contextually in the application.
        disable_external_notifications=True,
    )


def bot_commands(no_help_command: bool = False) -> str:
    commands = [
        "apps",
        "profile",
        "theme",
        "streams",
        "topics",
        "message formatting",
        "keyboard shortcuts",
    ]
    if not no_help_command:
        commands.append("help")
    return ", ".join(["`" + command + "`" for command in commands]) + "."


def select_welcome_bot_response(human_response_lower: str) -> str:
    # Given the raw (pre-markdown-rendering) content for a private
    # message from the user to Welcome Bot, select the appropriate reply.
    if human_response_lower in ["app", "apps"]:
        return _(
            "You can [download](/apps/) the [mobile and desktop apps](/apps/). "
            "Zulip also works great in a browser."
        )
    elif human_response_lower == "profile":
        return _(
            "Go to [Profile settings](#settings/profile) "
            "to add a [profile picture](/help/change-your-profile-picture) "
            "and edit your [profile information](/help/edit-your-profile)."
        )
    elif human_response_lower == "theme":
        return _(
            "Go to [Display settings](#settings/display-settings) "
            "to [switch between the light and dark themes](/help/dark-theme), "
            "[pick your favorite emoji theme](/help/emoji-and-emoticons#change-your-emoji-set), "
            "[change your language](/help/change-your-language), "
            "and make other tweaks to your Zulip experience."
        )
    elif human_response_lower in ["stream", "streams", "channel", "channels"]:
        return "".join(
            [
                _(
                    "In Zulip, streams [determine who gets a message](/help/streams-and-topics). "
                    "They are similar to channels in other chat apps."
                )
                + "\n\n",
                _("[Browse and subscribe to streams](#streams/all)."),
            ]
        )
    elif human_response_lower in ["topic", "topics"]:
        return "".join(
            [
                _(
                    "In Zulip, topics [tell you what a message is about](/help/streams-and-topics). "
                    "They are light-weight subjects, very similar to the subject line of an email."
                )
                + "\n\n",
                _(
                    "Check out [Recent conversations](#recent) to see what's happening! "
                    'You can return to this conversation by clicking "Direct messages" in the upper left.'
                ),
            ]
        )
    elif human_response_lower in ["keyboard", "shortcuts", "keyboard shortcuts"]:
        return "".join(
            [
                _(
                    "Zulip's [keyboard shortcuts](#keyboard-shortcuts) "
                    "let you navigate the app quickly and efficiently."
                )
                + "\n\n",
                _("Press `?` any time to see a [cheat sheet](#keyboard-shortcuts)."),
            ]
        )
    elif human_response_lower in ["formatting", "message formatting"]:
        return "".join(
            [
                _(
                    "Zulip uses [Markdown](/help/format-your-message-using-markdown), "
                    "an intuitive format for **bold**, *italics*, bulleted lists, and more. "
                    "Click [here](#message-formatting) for a cheat sheet."
                )
                + "\n\n",
                _(
                    "Check out our [messaging tips](/help/messaging-tips) "
                    "to learn about emoji reactions, code blocks and much more!"
                ),
            ]
        )
    elif human_response_lower in ["help", "?"]:
        return "".join(
            [
                _("Here are a few messages I understand:") + " ",
                bot_commands(no_help_command=True) + "\n\n",
                _(
                    "Check out our [Getting started guide](/help/getting-started-with-zulip), "
                    "or browse the [Help center](/help/) to learn more!"
                ),
            ]
        )
    else:
        return "".join(
            [
                _(
                    "I’m sorry, I did not understand your message. Please try one of the following commands:"
                )
                + " ",
                bot_commands(),
            ]
        )


def send_welcome_bot_response(send_request: SendMessageRequest) -> None:
    """Given the send_request object for a private message from the user
    to welcome-bot, trigger the welcome-bot reply."""
    welcome_bot = get_system_bot(settings.WELCOME_BOT, send_request.message.sender.realm_id)
    human_response_lower = send_request.message.content.lower()
    content = select_welcome_bot_response(human_response_lower)

    internal_send_private_message(
        welcome_bot,
        send_request.message.sender,
        content,
        # Note: Welcome bot doesn't trigger email/push notifications,
        # as this is intended to be seen contextually in the application.
        disable_external_notifications=True,
    )


@transaction.atomic
def send_initial_realm_messages(realm: Realm) -> None:
    welcome_bot = get_system_bot(settings.WELCOME_BOT, realm.id)
    # Make sure each stream created in the realm creation process has at least one message below
    # Order corresponds to the ordering of the streams on the left sidebar, to make the initial Home
    # view slightly less overwhelming
    content_of_private_streams_topic = (
        _("This is a private stream, as indicated by the lock icon next to the stream name.")
        + " "
        + _("Private streams are only visible to stream members.")
        + "\n"
        "\n"
        + _(
            "To manage this stream, go to [Stream settings]({stream_settings_url}) "
            "and click on `{initial_private_stream_name}`."
        )
    ).format(
        stream_settings_url="#streams/subscribed",
        initial_private_stream_name=Realm.INITIAL_PRIVATE_STREAM_NAME,
    )

    content1_of_topic_demonstration_topic = (
        _(
            "This is a message on stream #**{default_notification_stream_name}** with the "
            "topic `topic demonstration`."
        )
    ).format(default_notification_stream_name=Realm.DEFAULT_NOTIFICATION_STREAM_NAME)

    content2_of_topic_demonstration_topic = (
        _("Topics are a lightweight tool to keep conversations organized.")
        + " "
        + _("You can learn more about topics at [Streams and topics]({about_topics_help_url}).")
    ).format(about_topics_help_url="/help/streams-and-topics")

    content_of_swimming_turtles_topic = (
        _(
            "This is a message on stream #**{default_notification_stream_name}** with the "
            "topic `swimming turtles`."
        )
        + "\n"
        "\n"
        "[](/static/images/cute/turtle.png)"
        "\n"
        "\n"
        + _(
            "[Start a new topic]({start_topic_help_url}) any time you're not replying to a \
        previous message."
        )
    ).format(
        default_notification_stream_name=Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
        start_topic_help_url="/help/start-a-new-topic",
    )

    welcome_messages: List[Dict[str, str]] = [
        {
            "stream": Realm.INITIAL_PRIVATE_STREAM_NAME,
            "topic": "private streams",
            "content": content_of_private_streams_topic,
        },
        {
            "stream": Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
            "topic": "topic demonstration",
            "content": content1_of_topic_demonstration_topic,
        },
        {
            "stream": Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
            "topic": "topic demonstration",
            "content": content2_of_topic_demonstration_topic,
        },
        {
            "stream": realm.DEFAULT_NOTIFICATION_STREAM_NAME,
            "topic": "swimming turtles",
            "content": content_of_swimming_turtles_topic,
        },
    ]

    messages = [
        internal_prep_stream_message_by_name(
            realm,
            welcome_bot,
            message["stream"],
            message["topic"],
            message["content"],
        )
        for message in welcome_messages
    ]
    message_ids = do_send_messages(messages)

    # We find the one of our just-sent messages with turtle.png in it,
    # and react to it.  This is a bit hacky, but works and is kinda a
    # 1-off thing.
    turtle_message = Message.objects.select_for_update().get(
        id__in=message_ids, content__icontains="cute/turtle.png"
    )
    (emoji_code, reaction_type) = emoji_name_to_emoji_code(realm, "turtle")
    do_add_reaction(welcome_bot, turtle_message, "turtle", emoji_code, reaction_type)
