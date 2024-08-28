-- CREATE schema Delievery;
-- use Delievery;
SET FOREIGN_KEY_CHECKS = 0;


DROP TABLE IF EXISTS `AccountHolders`;
DROP TABLE IF EXISTS `GiftCards`;
DROP TABLE IF EXISTS `NotificationRecipients`;
DROP TABLE IF EXISTS `Notifications`;
DROP TABLE IF EXISTS `BoxOrders`;
DROP TABLE IF EXISTS `Boxes`;
DROP TABLE IF EXISTS `OrderItems`;
DROP TABLE IF EXISTS `OrderStatus`;
DROP TABLE IF EXISTS `Orders`;
DROP TABLE IF EXISTS `Products`;
DROP TABLE IF EXISTS `Payments`;
DROP TABLE IF EXISTS `Categories`;
DROP TABLE IF EXISTS `CustomerProfile`;
DROP TABLE IF EXISTS `StaffProfile`;
DROP TABLE IF EXISTS `Subscriptions`;
DROP TABLE IF EXISTS `Locations`;
DROP TABLE IF EXISTS `Users`;
DROP TABLE IF EXISTS `Roles`;
DROP TABLE IF EXISTS `Cart`;
DROP TABLE IF EXISTS `CartItems`;
DROP TABLE IF EXISTS `CreditIncreaseRequests`;
DROP TABLE IF EXISTS `Invoices`;
DROP TABLE IF EXISTS `InvoiceItems`;
DROP TABLE IF EXISTS `InquiryMsg`;
DROP TABLE IF EXISTS `Inquiries`;
DROP TABLE IF EXISTS `Units`;
DROP TABLE IF EXISTS `News`;
DROP TABLE IF EXISTS `GiftCardOption`;
DROP TABLE IF EXISTS `BoxContents`;
DROP TABLE IF EXISTS `Recipes`;
DROP TABLE IF EXISTS `Points`;
DROP TABLE IF EXISTS `PointsTransactions`;
DROP TABLE IF EXISTS `UserGiftCards`;

-- Enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;


-- Create Roles Table
CREATE TABLE Roles (
    RoleID INT AUTO_INCREMENT PRIMARY KEY,
    RoleName VARCHAR(255) NOT NULL
);

-- Users Table adjusted to reference Roles
CREATE TABLE Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Email VARCHAR(255) UNIQUE NOT NULL,
    Password VARCHAR(255) NOT NULL,
    RoleID INT,
    IsDeleted BOOLEAN,
    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
);

-- Locations Table
CREATE TABLE Locations (
    LocationID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Address VARCHAR(255),
    ShippingPrice DECIMAL(10,2)
);

-- CustomerProfile Table
CREATE TABLE CustomerProfile (
    UserID INT PRIMARY KEY,
    FirstName VARCHAR(255) NOT NULL,
    LastName VARCHAR(255) NOT NULL,
    Location VARCHAR(50) NOT NULL,
    LocationID INT,
    Address VARCHAR(255),
    Email VARCHAR(100),
    Phone VARCHAR(50),
    IFACCOUNTHOLDER ENUM('yes', 'no') NOT NULL,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (LocationID) REFERENCES Locations(LocationID)
);

-- StaffProfile Table
CREATE TABLE StaffProfile (
    UserID INT PRIMARY KEY,
    FirstName VARCHAR(255) NOT NULL,
    LastName VARCHAR(255) NOT NULL,
    Email VARCHAR(100),
    Phone VARCHAR(50),
    Location VARCHAR(50),
    LocationID INT,
    Department VARCHAR(255),
    Status ENUM('Active', 'Inactive'),  
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (LocationID) REFERENCES Locations(LocationID)
);

-- Categories Table
CREATE TABLE Categories (
    CategoryID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL
);

CREATE TABLE Units (
    UnitID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(50) NOT NULL
);

-- Products Table
CREATE TABLE Products (
    ProductID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Description TEXT,
    Price DECIMAL(10,2) NOT NULL,
    UnitID INT,
    CategoryID INT,
    AvailableQuantity INT,
    ImageURL VARCHAR(255),
    Available BIT DEFAULT 1,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (UnitID) REFERENCES Units(UnitID)
);


-- Orders Status Table
CREATE TABLE OrderStatus (
    StatusID INT AUTO_INCREMENT PRIMARY KEY,
    StatusName VARCHAR(255) NOT NULL
);

-- Orders Table
CREATE TABLE Orders (
    OrderID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    DateOrdered DATETIME NOT NULL,
    StatusID INT NOT NULL,
    TotalPrice DECIMAL(10,2),
    LocationID INT,
    DateUpdated DATETIME NULL,
    ShippingPrice DECIMAL(10,2),
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (LocationID) REFERENCES Locations(LocationID),
    FOREIGN KEY (StatusID) REFERENCES OrderStatus(StatusID)
);

-- OrderItems Table
CREATE TABLE OrderItems (
    OrderItemID INT AUTO_INCREMENT PRIMARY KEY,
    OrderID INT,
    ProductID INT,
    Quantity INT,
    UnitPrice DECIMAL(10,2),
    Unit ENUM('bunch', '500g', '1kg', 'each', 'half size', 'punnet', 'tray') NOT NULL,
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE CASCADE
);
CREATE TABLE Invoices (
    InvoiceID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    InvoiceDate DATE,
    DueDate DATE,
    TotalAmount DECIMAL(10, 2),
    GSTAmount DECIMAL(10, 2),
    ShippingPrice DECIMAL(10, 2),
    Status ENUM('Pending', 'Paid') DEFAULT 'Pending',
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

CREATE TABLE InvoiceItems (
    InvoiceItemID INT AUTO_INCREMENT PRIMARY KEY,
    InvoiceID INT,
    Description TEXT,
    Quantity INT,
    UnitPrice DECIMAL(10, 2),
    TotalPrice DECIMAL(10, 2),
    FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID)
);
-- Boxes Table
CREATE TABLE Boxes (
    BoxID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Type ENUM('Vegetable', 'Fruit', 'Mixed') NOT NULL,
    Size ENUM('Large', 'Medium', 'Small') NOT NULL,
    Price DECIMAL(10,2) NOT NULL,
    ContentsDescription TEXT,
    ImageURL VARCHAR(255)
);

CREATE TABLE BoxContents (
    BoxContentID INT AUTO_INCREMENT PRIMARY KEY,
    BoxID INT,
    ProductID INT,
    Quantity INT NOT NULL,
    FOREIGN KEY (BoxID) REFERENCES Boxes(BoxID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID) ON DELETE CASCADE
);

-- BoxOrders Table
CREATE TABLE BoxOrders (
    BoxOrderID INT AUTO_INCREMENT PRIMARY KEY,
    BoxID INT,
    UserID INT,
	StatusID INT NOT NULL,
    Quantity INT NOT NULL,
	TotalPrice DECIMAL(10,2),
	DateCreated DATETIME NULL,
    DateUpdated DATETIME NULL,
    FOREIGN KEY (BoxID) REFERENCES Boxes(BoxID),
    FOREIGN KEY (StatusID) REFERENCES OrderStatus (StatusID),
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

-- Inquiries Table 
CREATE TABLE Inquiries(
    InquiryID INT AUTO_INCREMENT PRIMARY KEY,
    -- CustomerID
    UserID INT,
    Subject VARCHAR(255),
    InquiryMsgID INT,
    DateCreated DATETIME,
    IfOpen bit default 1,
    FOREIGN KEY (UserID) REFERENCES CustomerProfile(UserID)
);
-- InquiryMsg Table
CREATE TABLE InquiryMsg(
    InquiryMsgID INT AUTO_INCREMENT PRIMARY KEY,
    InquiryID INT,
    UserID INT,
    Message VARCHAR(255),   
    DateCreated DATETIME,
    IfRead bit default 0,
    FOREIGN KEY (InquiryID) REFERENCES Inquiries(InquiryID),
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

-- Notifications Table
CREATE TABLE Notifications (
    NotificationID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    Type ENUM('Promotion', 'Order Update', 'Delivery Status', 'General Alert') NOT NULL,
    Title VARCHAR(255),
    Message TEXT,
    Link VARCHAR(255),
    DateCreated DATETIME,
    ExpirationDate DATETIME,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

CREATE TABLE NotificationRecipients (
    RecipientID INT,
    NotificationID INT,
    HasBeenRead BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (RecipientID, NotificationID),
    FOREIGN KEY (RecipientID) REFERENCES Users(UserID),
    FOREIGN KEY (NotificationID) REFERENCES Notifications(NotificationID)
);
-- Subscriptions Table
CREATE TABLE Subscriptions (
    SubID INT AUTO_INCREMENT PRIMARY KEY,
    BoxID INT NOT NULL,
    UserID INT NOT NULL,
    Quantity INT NOT NULL,
    Frequency ENUM('One-time', 'Weekly', 'Fortnightly', 'Monthly') NOT NULL,
    Status ENUM ('Active', 'Inactive') DEFAULT 'Active',
    StartDate DATETIME NOT NULL,
    EndDate DATETIME NOT NULL,
    DateCreated DATETIME NOT NULL,
    TotalPrice DECIMAL(10,2),
    
    FOREIGN KEY (BoxID) REFERENCES Boxes(BoxID),
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

-- Payments Table
CREATE TABLE Payments (
    PaymentID INT AUTO_INCREMENT PRIMARY KEY,
    BoxOrderID INT NULL,
    OrderID INT NULL,
    InvoiceID  INT Null,
    CardNumber VARCHAR(255),
    CardHolder VARCHAR(255),
    Type ENUM('Subscription', 'Order', 'Invoice') NOT NULL,
    CreatedAt DATETIME,
    FOREIGN KEY (BoxOrderID) REFERENCES BoxOrders(BoxOrderID),
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
    FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID)
);


-- AccountHolders Table
CREATE TABLE AccountHolders (
    AccountHolderID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    BusinessName VARCHAR(255),
    BusinessAddress VARCHAR(255),
    BusinessContactNumber VARCHAR(50),
    CreditLimit DECIMAL(10,2),
    RemainingCredit DECIMAL(10,2),
    InvoiceDueDate DATE,
    ApplicationStatus ENUM('Pending', 'Approved', 'Rejected', 'Not Applied') DEFAULT 'Not Applied',
    ApplicationTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);


CREATE TABLE CreditIncreaseRequests (
    RequestID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    RequestedAmount DECIMAL(10,2) NOT NULL,
    Reason TEXT,
    Status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    RequestTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)

);

-- Cart Table
CREATE TABLE Cart (
    CartID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    DateCreated DATETIME DEFAULT CURRENT_TIMESTAMP,
    GiftCard VARCHAR(255),
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

-- CartItems Table
CREATE TABLE CartItems (
    CartItemID INT AUTO_INCREMENT PRIMARY KEY,
    CartID INT,
    ProductID INT,
    Quantity INT,
    UnitPrice DECIMAL(10,2),
    Unit ENUM('bunch', '500g', '1kg', 'each', 'half size', 'punnet', 'tray') NOT NULL,
    FOREIGN KEY (CartID) REFERENCES Cart(CartID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

-- News Table
CREATE TABLE News (
    NewsID INT AUTO_INCREMENT PRIMARY KEY,
    NewsType ENUM('Promotion', 'General'),
    Title TEXT,
    Message TEXT,
    DateCreated DATETIME DEFAULT CURRENT_TIMESTAMP,
    ExpirationDate DATE,
    LocationID INT,
    FOREIGN KEY (LocationID) REFERENCES Locations(LocationID)
    
);

CREATE TABLE GiftCardOption (
	GiftCardOptionID INT AUTO_INCREMENT PRIMARY KEY,
    GiftCardName VARCHAR(25),
    Value INT,
    Image VARCHAR(255)
);

CREATE TABLE Recipes (
    RecipeID INT AUTO_INCREMENT PRIMARY KEY,
    ProductID INT,
    RecipeName VARCHAR(255) NOT NULL,
    Ingredients TEXT,
    Instructions TEXT,
    ImageURL VARCHAR(255),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

-- GiftCards Table
CREATE TABLE GiftCards (
    GiftCardID INT AUTO_INCREMENT PRIMARY KEY,
    CardNumber VARCHAR(255) NOT NULL,
    Balance DECIMAL(10,2),
    Type INT NOT NULL,
    Name VARCHAR(255) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    dateCreated DATE,
    FOREIGN KEY (Type) REFERENCES GiftCardOption(GiftCardOptionID)
);

CREATE TABLE UserGiftCards (
    UserGiftCardID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    GiftCardID INT,
    DatePurchased DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (GiftCardID) REFERENCES GiftCards(GiftCardID)
);

CREATE TABLE Points (
    PointsID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    CurrentPoints INT DEFAULT 0,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

CREATE TABLE PointsTransactions (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT,
    OrderID INT NULL,
    PointsEarned INT,
    PointsDeducted INT,
    TransactionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID)
);


-- Insert Role
INSERT INTO Roles (RoleName) VALUES ('Customer'), ('Staff'), ('LocalManager'), ('NationalManager');

-- Insert Users
INSERT INTO Users (Email, Password, RoleID) VALUES
('customer@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('staff@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('localmanager@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 3),
('nationalmanager@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 4),
('staff01@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff02@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff03@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff04@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff05@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff06@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff07@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff08@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff09@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('staff10@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 2),
('customer11@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer12@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer13@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer14@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer15@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer16@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer17@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer18@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer19@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1),
('customer20@gmail.com', 'dbd9a47be978b75a020ed6073088f5c9e686fccbeffa16877d916ad3e173c47b', 1);

-- Insert Locations
INSERT INTO Locations (LocationID, Name, Address, ShippingPrice) VALUES
(1, 'Auckland', '456 Maple Ave, Auckland', 5.00),
(2, 'Christchurch', '123 Oak St, Christchurch', 5.00),
(3, 'Hamilton', '22 Oak St, Hamilton', 5.00),
(4, 'Invercargill', '23 Oak St, Invercargill', 5.00),
(5, 'Wellington', '77 Maple Ave, Wellington', 5.00);

-- Insert CustomerProfile
INSERT INTO CustomerProfile (UserID, FirstName, LastName, LocationID, Location, Address, Email, Phone, IFACCOUNTHOLDER) VALUES
(1, 'John', 'Harden', 5, 'Wellington', '123 Elm St, Wellington', 'customer@gmail.com', '0212345678', 'no'),
(15, 'William', 'Caya', 5, 'Wellington', '13 Wef St, Wellington', 'customer11@gmail.com', '0212345678', 'no'),
(16, 'Emmaly', 'Wong', 4, 'Invercargill', '12 Elm St, Invercargill', 'customer12@gmail.com', '0212345678', 'no'),
(17, 'James', 'Leborn', 4, 'Invercargill', '1 Elm St, Invercargill', 'customer13@gmail.com', '0212345678', 'no'),
(18, 'Olivia', 'James', 3, 'Hamilton', '23 Elm St, Hamilton', 'customer14@gmail.com', '0212345678', 'no'),
(19, 'Benjamin', 'Cai', 3, 'Hamilton', '3 Elm St, Hamilton', 'customer15@gmail.com', '0212345678', 'no'),
(20, 'Sophia', 'Judi', 2, 'Christchurch', '123 Elm St, Christchurch', 'customer16@gmail.com', '0212345678', 'no'),
(21, 'Michael', 'Lucy', 2, 'Christchurch', '13 Elm St, Christchurch', 'customer17@gmail.com', '0212345678', 'no'),
(22, 'Isabella', 'Joel', 1, 'Auckland', '123 Elm St, Auckland', 'customer18@gmail.com', '0212345678', 'no'),
(23, 'Alexander', 'Win', 1, 'Auckland', '123 Elm St, Auckland', 'customer19@gmail.com', '0212345678', 'no'),
(24, 'Damian', 'Zhang', 5, 'Wellington', '12 Elm St, Wellington', 'customer20@gmail.com', '0212345678', 'no');
-- Insert StaffProfile
INSERT INTO StaffProfile (UserID, FirstName, LastName, Phone, Email, LocationID, Location, Department, Status) VALUES
(2, 'Jane', 'Smith', '0212345678', 'staff@gmail.com', 2, 'Christchurch', 'Sales', 'Active'),
(3, 'Lily', 'Wong', '0212345679', 'localmanager@gmail.com', 2, 'Christchurch', 'Local Manager', 'Active'),
(4, 'Johnny', 'White', '0212345978', 'nationalmanager@gmail.com', 2, 'Christchurch', 'National Manager', 'Active'),
(5, 'John', 'Doe', '0212345679', 'staff01@gmail.com', 1, 'Auckland', 'Marketing', 'Active'),
(6, 'Emma', 'Brown', '0212345680', 'staff02@gmail.com', 5, 'Wellington', 'Finance', 'Active'),
(7, 'Liam', 'Wilson', '0212345681', 'staff03@gmail.com', 3, 'Hamilton', 'IT', 'Active'),
(8, 'Olivia', 'Taylor', '0212345682', 'staff04@gmail.com', 2, 'Christchurch', 'HR', 'Active'),
(9, 'Noah', 'Davis', '0212345683', 'staff05@gmail.com', 4, 'Invercargill', 'Operations', 'Active'),
(10, 'Sophia', 'Martin', '0212345684', 'staff06@gmail.com', 1, 'Auckland', 'Logistics', 'Active'),
(11, 'Mason', 'Lee', '0212345685', 'staff07@gmail.com', 5, 'Wellington', 'R&D', 'Active'),
(12, 'Isabella', 'White', '0212345686', 'staff08@gmail.com', 3, 'Hamilton', 'Customer Service', 'Active'),
(13, 'Ethan', 'Harris', '0212345687', 'staff09@gmail.com', 2, 'Christchurch', 'Legal', 'Active'),
(14, 'Ava', 'Clark', '0212345688', 'staff10@gmail.com', 4, 'Invercargill', 'Sales', 'Active');



-- Insert Categories
INSERT INTO Categories (Name) VALUES
('Fruits'),
('Vegetables'),
('Herbs'),
('Eggs'),
('Honey');

INSERT INTO Units (Name) VALUES
('Bunch'),
('500g'),
('1kg'),
('Each'),
('Half size'),
('Punnet'),
('Tray');

-- Insert Products
INSERT INTO Products (Name, Description, Price, UnitID, CategoryID, AvailableQuantity, ImageURL) VALUES
('Apple', 'Fresh apples', 2.50, 3, 1, 100, 'product-1.jpg'),
('Banana', 'Organic bananas', 3.00, 3, 1, 150, 'product-8.jpg'),
('Chilli', 'Spicy Chilli', 1.75, 2, 2, 200, 'product-3.jpg'),
('Potato', 'Potatoes', 2.00, 2, 2, 150, 'product-7.jpg'),
('Strawberry', 'Fresh fruits', 5.00, 6, 1, 80, 'product-4.jpg'),
('Cucumber', 'Fresh vegetables', 2.00, 4, 2, 80, 'product-5.jpg'),
('Tomatoes', 'Fresh vegetables', 6.99, 3, 2, 80, 'product-6.jpg'),
('Pinapple', 'Fresh fruits', 3.99, 4, 1, 80, 'product-2.jpg'),
('Bay leaf', 'herbs', 3.50, 1, 3, 80, 'product-9.jpg'),
('Eggs', 'Eggs', 6.99,7, 4, 80, 'product-10.jpg'),
('Honey', 'Honey', 12.50, 2, 5, 80, 'product-11.jpg');

INSERT INTO Recipes (ProductID, RecipeName, Ingredients, Instructions, ImageURL) VALUES
(4, "Best Potatoes You'll Ever Taste", "3 tablespoons mayonnaise, 2 cloves garlic, crushed, 1 teaspoon dried oregano, salt and pepper to taste, 5 potatoes, quartered ", 
  "Gather all ingredients, In a small bowl, mix mayonnaise, garlic, oregano, salt , and pepper. Set aside. Bring a large pot of salted water to a boil. Add potatoes, and cook until almost done, about 10 minutes. Don't overcook otherwise the potatoes will break apart. Drain, and cool. Preheat oven broiler. Line a baking tray with aluminum foil, and lightly grease the aluminum foil. Arrange potatoes in the prepared baking tray. Spoon the mayonnaise mixture over the potatoes. Broil in the preheated oven until potatoes are tender and mayonnaise mixture is lightly browned, about 10 minutes. Serve hot and enjoy!",
  'recipe-3.jpg'),

(6, "Cucumber Salad","4 cucumbers, thinly sliced, 1 small white onion, thinly sliced, 1 cup white vinegar, ¾ cup white sugar, ½ cup water, 1 tablespoon dried dill, or to taste ",
 "Toss sliced cucumbers and onion together in a large bowl. Set aside.Combine vinegar, sugar, and water in a saucepan over medium-high heat; bring to a boil; pour over cucumbers and onions in the bowl. Stir in dill. Cover and let marinate in the refrigerator for at least 1 hour before serving." , 
 'recipe-2.jpg'),
 
(7, "Scrambled Eggs and Tomatoes", "2 large eggs, beaten, 2 tomatoes, coarsely chopped, 1 ½ teaspoons sugar, salt to taste, 1 dash soy sauce " , 
"In a skillet over medium heat, scramble eggs until almost done. Remove to a plate.Return skillet to medium heat, and stir in tomatoes. Cook 2 to 3 minutes. Stir in sugar, salt, and soy. Return eggs to skillet; cook, stirring, about 1 minute more." , 
'recipe-1.jpg');



-- Insert OrderStatus
INSERT INTO OrderStatus (StatusName) VALUES ('Pending');
INSERT INTO OrderStatus (StatusName) VALUES ('Processing');
INSERT INTO OrderStatus (StatusName) VALUES ('Delivering');
INSERT INTO OrderStatus (StatusName) VALUES ('Ready for Delivery');
INSERT INTO OrderStatus (StatusName) VALUES ('Delivered');
INSERT INTO OrderStatus (StatusName) VALUES ('Cancelled');

-- Insert Orders
INSERT INTO Orders (OrderID, UserID, DateOrdered, StatusID, TotalPrice, LocationID, ShippingPrice) VALUES
(1, 16, '2024-05-01 10:30:00', 1, 13.00, 4, 5),
(2, 20, '2024-05-03 14:00:00', 3, 24.99, 2, 5),  
(3, 21, '2024-05-04 16:15:00', 2, 27.50, 2, 5), 
(4, 1, '2024-05-05 10:45:00', 1, 13.25, 5, 5),
(5, 1, '2024-05-06 09:20:00', 3, 7.50, 5, 5),
(6, 1, '2024-05-07 13:30:00', 2, 11.00, 5, 5),
(7, 17, '2024-05-08 15:00:00', 3, 60.25, 4, 5),
(8, 18, '2024-05-09 11:45:00', 2, 55.55, 3, 5),
(9, 19, '2024-05-10 12:30:00', 3, 40.00, 3, 5),
(10, 15, '2024-05-11 17:00:00', 1, 33.75, 5, 5), 
(11, 23, '2024-05-11 17:30:00', 1, 7.00, 1, 5);

-- Insert OrderItems
INSERT INTO OrderItems (OrderID, ProductID, Quantity, UnitPrice, Unit) VALUES
(1, 1, 2, 2.50, 'each'),
(4, 1, 3, 2.75, 'each'),
(5, 1, 1, 2.50, 'each'),
(6, 2, 2, 3.00, 'each'),
(1, 2, 1, 3.00, 'bunch');



-- Insert Boxes
INSERT INTO Boxes (Name, Type, Size, Price, ContentsDescription, ImageURL) VALUES
('Standard Vegetable Box', 'Vegetable', 'Large', 50.00, 'Carrots, Broccoli, Spinach', 'box-1.jpg'),
('Standard Fruit Box', 'Fruit', 'Medium', 30.00, 'Apples, Oranges, Bananas, Grapes', 'box-2.jpg'),
('Standard Mixed Box', 'Mixed', 'Small', 20.00, 'Carrots, Apples, Broccoli, Oranges', 'box-3.jpg'),
('Deluxe Vegetable Box', 'Vegetable', 'Large', 50.00, 'Carrots, Broccoli, Spinach, Potatoes, Tomatoes', 'box-1.jpg'),
('Deluxe Fruit Box', 'Fruit', 'Medium', 30.00, 'Apples, Oranges, Bananas, Grapes, Peaches, Kiwifruit', 'box-2.jpg'),
('Deluxe Mixed Box', 'Mixed', 'Small', 20.00, 'Carrots, Apples, Broccoli, Oranges, Peaches, Beans', 'box-3.jpg');

-- Insert BoxContents 
INSERT INTO BoxContents  (BoxID , ProductID , Quantity) VALUES
(1,3,2),
(1,4,2),
(1,6,3),
(1,7,2),
(2,1,2),
(2,2,2),
(2,5,2),
(3,1,1),
(3,2,1),
(3,6,2),
(3,7,1),
(4,3,3),
(4,4,3),
(4,6,5),
(4,7,3),
(5,8,2),
(5,5,3),
(5,2,3),
(6,1,3),
(6,8,2),
(6,6,3),
(6,7,2);

-- Insert BoxOrders
-- INSERT INTO BoxOrders (BoxID, OrderID, Frequency) VALUES
-- (1, 1, 'Weekly');

-- Insert Notifications
INSERT INTO Notifications (UserID, Type, Title, Message, Link, DateCreated, ExpirationDate)
VALUES (4, 'Promotion', 'Weekly Special', '20% off on all fruit boxes!', 'http://example.com/special', NOW(), '2024-06-01 23:59:59');

-- Insert Notification Recipients
INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (2, 1);
INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (3, 1);
INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (6, 1);



INSERT INTO News (NewsType, Title, Message, DateCreated, ExpirationDate) VALUES ('Promotion', '20% ENDS This Week!!', 'Get 20% OFF on all orders at Fresh Delivery only on this week! Don''t miss out – this amazing deal ends today! Shop now and save big!', '2024-06-01 22:13:09', '2024-06-20'),
('Promotion', 'Enjoy Free Delivery', 'Order now and get your items delivered to your doorstep at no extra cost on 23/05/2024. Don''t miss out on this.', '2024-05-23 00:00:00', '2024-06-01'),
('General', 'Fresh Delivery now delivers to Christchurch', 'Fresh Delivery now delivers to Christchurch! Enjoy our fresh products straight to your doorstep. Order today and experience the convenience!', '2024-01-01 22:13:09','2024-06-20'),
('General', 'Introducing the Deluxe Fruit Box', 'Discover a premium selection of fresh, hand-picked fruits delivered straight to your door. Taste the luxury today!', '2024-03-01 22:13:09','2024-06-01');

INSERT INTO News (NewsType, Title, Message, DateCreated, ExpirationDate, LocationID) VALUES ('Promotion', 'Enjoy Free mystery box when spend over $50 THIS WEEK', 'Order now and get your free mystery box for order over $50 THIS WEEK. Don''t miss out on this.', '2024-06-19 00:00:00', '2024-06-10', 2);

-- Invoices 
INSERT INTO Invoices (UserID, InvoiceDate, DueDate, TotalAmount, GSTAmount, ShippingPrice, Status)
VALUES 
(1, '2024-05-01', '2024-05-01', 25.75, 3.36, 5.00, 'Paid'),
(1, '2024-05-03', '2024-05-03', 19.99, 2.60, 5.00, 'Paid'),
(1, '2024-05-04', '2024-05-04', 22.50, 2.93, 5.00, 'Paid');

-- Invoice Items for InvoiceID 1
INSERT INTO InvoiceItems (InvoiceID, Description, Quantity, UnitPrice, TotalPrice) VALUES
(1, 'Apple', 2, 2.50, 5.00),
(1, 'Banana', 1, 3.00, 3.00);

-- Invoice Items for InvoiceID 2
INSERT INTO InvoiceItems (InvoiceID, Description, Quantity, UnitPrice, TotalPrice) VALUES
(2, 'Apple', 3, 2.75, 8.25),
(2, 'Banana', 1, 2.50, 2.50);


-- Invoice Items for InvoiceID 3
INSERT INTO InvoiceItems (InvoiceID, Description, Quantity, UnitPrice, TotalPrice) VALUES
(3, 'Chilli', 2, 3.00, 6.00),
(3, 'Potato', 1, 3.00, 3.00);



-- Insert Payments
INSERT INTO Payments (OrderID, CardNumber, CardHolder, InvoiceID, Type, CreatedAt) VALUES
(1,  '4485 8264 8634 4751', 'Mike Brown', 1, 'Order', '2024-06-01 10:45:00'),
(2,  '4539 5738 7464 4382', 'Mike Brown', 2, 'Order', '2024-05-02 09:20:00'),
(3,  '4716 6210 9387 6185', 'Mike Brown', 3, 'Order', '2024-05-03 13:30:00');



-- Insert Subscriptions
INSERT INTO Subscriptions
(BoxID, UserID, Quantity, Frequency, Status, StartDate, EndDate, DateCreated, TotalPrice)
VALUES
(
    1, 1, 2, 'Weekly', 'Active', DATE_SUB(NOW(), INTERVAL 7 DAY), NOW(),
    DATE_SUB(NOW(), INTERVAL 7 DAY), 50.00 
);



INSERT INTO GiftCardOption(GiftCardName, Value, Image) VALUES ('General Gift Card', 100, 'gc.jpeg'),
('Birthday Card', 100, 'gcbd.png'),
('Christmas Card', 100, 'gcchr.jpg'),
('Thank You Card', 100, 'gcty.jpeg');

-- Insert GiftCards
INSERT INTO GiftCards (CardNumber, Balance,Type, Name, Address ,dateCreated ) VALUES
('1234567890', 50.00, 1 , "Fred", "1 Road, Auckland", "2024-06-09" );

-- Insert InvoiceItems
INSERT INTO InvoiceItems (InvoiceID, Description, Quantity, UnitPrice, TotalPrice)
VALUES (1, 'Strawberry', 1, 5.00, 5.00),
       (2, 'Apple', 1, 2.50, 2.50),
       (3, 'Banana', 2, 3.00, 6.00);

