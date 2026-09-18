import type { Lang } from "./i18n";

/**
 * Advisor biographies for the "Biography" sheet on the home screen. Localized like the
 * names and roles in `agents.ts`: structured content that a flat key/value catalog would
 * only make harder to read and edit.
 */
export interface Biography {
  years: string;
  subtitle: string;
  paragraphs: string[];
  helps: string;
  cases: string[];
}

export const BIOGRAPHIES: Record<string, Record<Lang, Biography>> = {
  aurelius: {
    ru: {
      years: "121–180",
      subtitle: "Римский император и философ-стоик",
      paragraphs: [
        "Марк Аврелий управлял Римской империей в годы войн и эпидемии. Огромная власть не избавляла его от потерь, усталости, тревоги и необходимости принимать тяжёлые решения. Стоическая философия служила ему ежедневной практикой самообладания и ответственности.",
        "В личных записях, известных сегодня как «Наедине с собой», он напоминал себе о быстротечности жизни, необходимости поступать справедливо и ограниченности человеческого контроля. Он возвращался к вопросу: как сохранить достойное поведение, когда обстоятельства и поступки других людей не соответствуют твоим ожиданиям?",
      ],
      helps:
        "С чем поможет агент: отделить то, на что Вы можете повлиять, от того, что приходится принять. Поможет осмыслить свою реакцию и выбрать доступное действие, сохраняя верность собственным принципам.",
      cases: [
        "Планы рушатся из-за обстоятельств вне Вашего контроля.",
        "Вы переживаете из-за чужих слов или поступков.",
        "Приходится ждать решения, которое принимают другие.",
        "Нужно выдержать неудачу и продолжить действовать.",
        "Хочется вернуть внимание к тому, что действительно зависит от Вас.",
      ],
    },
    en: {
      years: "121–180",
      subtitle: "Roman emperor and Stoic philosopher",
      paragraphs: [
        "Marcus Aurelius ruled the Roman Empire through years of war and plague. Immense power did not spare him loss, exhaustion, anxiety or the need to make hard decisions. Stoic philosophy served him as a daily practice of self-command and responsibility.",
        "In the private notes known today as the Meditations he reminded himself of the brevity of life, the duty to act justly and the narrow limits of human control. He kept returning to one question: how to remain decent when circumstances and other people fall short of your expectations?",
      ],
      helps:
        "What the advisor helps with: separating what you can influence from what you have to accept. He helps you make sense of your own reaction and choose the action that is available to you, while staying true to your principles.",
      cases: [
        "Plans collapse because of circumstances beyond your control.",
        "Someone's words or actions keep weighing on you.",
        "You are waiting for a decision that others will make.",
        "You need to absorb a failure and keep going.",
        "You want to bring your attention back to what truly depends on you.",
      ],
    },
  },
  machiavelli: {
    ru: {
      years: "1469–1527",
      subtitle: "Флорентийский дипломат и политический мыслитель",
      paragraphs: [
        "Макиавелли жил в Италии, где города соперничали за власть, союзы быстро распадались, а вчерашние партнёры становились врагами. На дипломатической службе он встречался с правителями, участвовал в переговорах и наблюдал, как принимаются решения, от которых зависят судьбы государств.",
        "После возвращения семьи Медичи к власти во Флоренции он потерял должность. Отстранённый от политики, Макиавелли изложил свои наблюдения в «Государе» — книге о власти, человеческих мотивах и способности действовать в изменчивых обстоятельствах. Его интересовало, почему одни правители удерживают своё положение, а другие теряют его, несмотря на хорошие намерения.",
      ],
      helps:
        "С чем поможет агент: разобраться в интересах участников, подготовиться к сложному разговору и выбрать стратегию переговоров. Предложит посмотреть на ситуацию глазами другой стороны, оценить свои возможности и продумать последствия каждого хода.",
      cases: [
        "Договориться о повышении зарплаты или условиях сотрудничества.",
        "Защитить свои интересы под давлением.",
        "Разобраться в рабочем конфликте и расстановке сил.",
        "Понять, где стоит уступить, а где — обозначить границы.",
      ],
    },
    en: {
      years: "1469–1527",
      subtitle: "Florentine diplomat and political thinker",
      paragraphs: [
        "Machiavelli lived in an Italy where cities competed for power, alliances fell apart quickly and yesterday's partners became enemies. In the diplomatic service he met rulers, took part in negotiations and watched how decisions that shaped the fate of states were actually made.",
        "When the Medici returned to power in Florence he lost his post. Pushed out of politics, he set down his observations in The Prince, a book about power, human motives and the ability to act in shifting circumstances. He wanted to know why some rulers hold their position while others lose it despite good intentions.",
      ],
      helps:
        "What the advisor helps with: understanding the interests of everyone involved, preparing for a difficult conversation and choosing a negotiation strategy. He will suggest seeing the situation through the other side's eyes, weighing your options and thinking through the consequences of every move.",
      cases: [
        "Negotiating a raise or the terms of a partnership.",
        "Defending your interests under pressure.",
        "Making sense of a conflict at work and the balance of power in it.",
        "Seeing where to yield and where to draw a line.",
      ],
    },
  },
  jung: {
    ru: {
      years: "1875–1961",
      subtitle: "Швейцарский психиатр, основатель аналитической психологии",
      paragraphs: [
        "Юнг посвятил жизнь исследованию внутреннего мира человека: сновидений, символов, бессознательных мотивов и противоречий. Он был близким соратником Зигмунда Фрейда, однако расхождения во взглядах привели его к созданию собственного направления в психологии.",
        "Одной из центральных тем Юнга стала «тень» — стороны себя, которые человек не замечает, отвергает или не хочет признавать. К ним могут относиться агрессия, зависть, уязвимость, а также подавленные желания и способности. Юнг исследовал, как знакомство с этими сторонами помогает человеку лучше понимать себя и становиться более целостным.",
      ],
      helps:
        "С чем поможет агент: исследовать чувства, внутренние конфликты и повторяющиеся сценарии. Через вопросы и возможные объяснения поможет заметить связь между Вашими желаниями, страхами и поступками.",
      cases: [
        "Вы не понимаете, чего хотите на самом деле.",
        "Снова оказываетесь в похожих конфликтах или отношениях.",
        "Чужое мнение сильно влияет на Ваши решения.",
        "Достигаете целей, но не чувствуете удовлетворения.",
        "Хотите разобраться, почему определённый человек вызывает такую сильную реакцию.",
      ],
    },
    en: {
      years: "1875–1961",
      subtitle: "Swiss psychiatrist, founder of analytical psychology",
      paragraphs: [
        "Jung devoted his life to exploring the inner world: dreams, symbols, unconscious motives and contradictions. He was a close associate of Sigmund Freud, but their differences led him to found his own school of psychology.",
        "One of his central themes was the shadow, the sides of ourselves we overlook, reject or refuse to admit. They may include aggression, envy and vulnerability, as well as suppressed desires and abilities. Jung studied how meeting these sides helps a person understand themselves better and become more whole.",
      ],
      helps:
        "What the advisor helps with: exploring feelings, inner conflicts and recurring patterns. Through questions and possible explanations he helps you notice the link between your desires, fears and actions.",
      cases: [
        "You do not know what you really want.",
        "You keep ending up in similar conflicts or relationships.",
        "Other people's opinions weigh heavily on your decisions.",
        "You reach your goals but feel no satisfaction.",
        "You want to understand why a particular person provokes such a strong reaction in you.",
      ],
    },
  },
};
